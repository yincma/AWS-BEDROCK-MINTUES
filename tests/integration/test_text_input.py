"""
集成测试: 文字输入流程 (T011)

测试场景: 验证文字输入跳过Transcribe步骤,直接调用Nova Pro处理

测试流程:
1. POST /meetings with input_type=text, text_content="会议文字记录..."
2. 验证系统跳过Transcribe步骤
3. 直接调用Nova Pro处理文字
4. 验证生成的draft内容
5. 验证meeting.input_type="text"且无audio_key

关键断言:
- 文字输入应该比音频快(无转录时间)
- 不应该调用Transcribe service
- original_text应该直接是用户输入
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, Mock, patch
import time
from datetime import datetime

# 测试必须失败 - 应用尚未实现
pytestmark = pytest.mark.integration


class TestTextInputFlow:
    """文字输入流程集成测试"""

    @pytest.fixture
    def sample_text_content(self):
        """测试用文字内容"""
        return """
今天会议讨论了三个主要议题:

1. Q4产品路线图规划
发言人张三: 我认为应该优先开发AI推荐功能,这是用户反馈最多的需求
发言人李四: 我同意,但是需要先解决数据质量问题

2. 用户反馈分析
发言人王五: 上周收集了500条用户反馈,主要集中在性能和易用性
发言人张三: 建议下周开专题会讨论

3. 技术债务优先级
发言人李四: 目前有3个P0级别的技术债务需要处理
发言人王五: 建议分配2个sprint来解决

决策:
- 优先开发AI推荐功能
- 下周召开用户反馈专题会
- 分配2个sprint解决技术债务

行动项:
- 张三: 完成AI功能PRD (截止日期: 10-08)
- 李四: 分析用户反馈数据 (截止日期: 10-05)
- 王五: 评估技术债务工作量 (截止日期: 10-06)
"""

    @pytest.fixture
    def mock_bedrock_response(self):
        """模拟Bedrock Nova Pro响应"""
        return {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": """# 会议记录

## 会议基本信息
- 会议主题: Q4产品规划会议
- 会议日期: 2025-10-01
- 参与者: 张三, 李四, 王五

## 讨论议题
1. Q4产品路线图规划
   - 优先开发AI推荐功能
   - 需要先解决数据质量问题
2. 用户反馈分析
   - 收集了500条用户反馈
   - 主要问题: 性能和易用性
3. 技术债务优先级
   - 3个P0级别技术债务
   - 需要2个sprint解决

## 决策事项
- 决策1: 优先开发AI推荐功能
- 决策2: 下周召开用户反馈专题会
- 决策3: 分配2个sprint解决技术债务

## 行动项
- [ ] 张三: 完成AI功能PRD (截止日期: 10-08)
- [ ] 李四: 分析用户反馈数据 (截止日期: 10-05)
- [ ] 王五: 评估技术债务工作量 (截止日期: 10-06)
"""
                        }
                    ]
                }
            }
        }

    @pytest.mark.asyncio
    async def test_text_input_creates_meeting_successfully(
        self, sample_text_content
    ):
        """测试1: 文字输入成功创建会议记录"""
        # 导入FastAPI应用 - 预期失败: 模块不存在
        from src.api.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 发送POST请求,使用文字输入
            response = await client.post(
                "/api/v1/meetings",
                data={
                    "input_type": "text",
                    "text_content": sample_text_content,
                },
            )

            # 断言: 返回202 Accepted (异步处理)
            assert response.status_code == 202

            # 断言: 响应包含meeting_id
            data = response.json()
            assert "id" in data
            assert "status" in data
            assert data["status"] in ["draft", "processing"]

            # 断言: 包含预估完成时间(应该比音频快)
            assert "estimated_completion_time" in data
            # 文字输入预估时间应小于60秒(无转录时间)
            assert data["estimated_completion_time"] < 60

    @pytest.mark.asyncio
    async def test_text_input_skips_transcription_service(
        self, sample_text_content, mock_bedrock_response
    ):
        """测试2: 验证文字输入跳过Transcribe步骤"""
        from src.api.main import app
        from src.services.transcription_service import TranscriptionService
        from src.services.ai_service import AIService

        # Mock Transcribe服务 - 不应该被调用
        with patch.object(
            TranscriptionService, "transcribe_audio", new_callable=AsyncMock
        ) as mock_transcribe:
            # Mock Bedrock服务 - 应该被调用
            with patch.object(
                AIService,
                "extract_meeting_info",
                new_callable=AsyncMock,
                return_value=mock_bedrock_response["output"]["message"]["content"][0][
                    "text"
                ],
            ) as mock_bedrock:

                async with AsyncClient(app=app, base_url="http://test") as client:
                    # 创建文字输入会议
                    response = await client.post(
                        "/api/v1/meetings",
                        data={
                            "input_type": "text",
                            "text_content": sample_text_content,
                        },
                    )

                    meeting_id = response.json()["id"]

                    # 等待处理完成(最多30秒)
                    for _ in range(30):
                        status_response = await client.get(
                            f"/api/v1/meetings/{meeting_id}"
                        )
                        meeting_data = status_response.json()

                        if meeting_data["status"] in ["draft", "completed"]:
                            break
                        await asyncio.sleep(1)

                    # 断言: Transcribe服务未被调用
                    mock_transcribe.assert_not_called()

                    # 断言: Bedrock服务被调用
                    mock_bedrock.assert_called_once()

                    # 断言: Bedrock调用参数中的transcript是原始文字
                    call_args = mock_bedrock.call_args
                    assert sample_text_content in str(call_args)

    @pytest.mark.asyncio
    async def test_text_input_direct_ai_processing(
        self, sample_text_content, mock_bedrock_response
    ):
        """测试3: 验证文字直接进入AI处理流程"""
        from src.api.main import app
        import asyncio

        # 使用moto模拟AWS服务
        from moto import mock_aws
        import boto3

        with mock_aws():
            # 创建测试S3 bucket
            s3_client = boto3.client("s3", region_name="us-east-1")
            s3_client.create_bucket(Bucket="test-meeting-minutes")

            # Mock Bedrock响应
            bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")

            async with AsyncClient(app=app, base_url="http://test") as client:
                start_time = time.time()

                # 创建文字输入会议
                response = await client.post(
                    "/api/v1/meetings",
                    data={
                        "input_type": "text",
                        "text_content": sample_text_content,
                    },
                )

                assert response.status_code == 202
                meeting_id = response.json()["id"]

                # 轮询直到完成
                max_wait_time = 30  # 文字输入应该很快完成
                for _ in range(max_wait_time):
                    status_response = await client.get(
                        f"/api/v1/meetings/{meeting_id}"
                    )
                    meeting_data = status_response.json()

                    if meeting_data["status"] == "draft":
                        break
                    await asyncio.sleep(1)

                processing_time = time.time() - start_time

                # 断言: 处理时间应该快(无转录步骤)
                assert (
                    processing_time < 30
                ), f"文字输入处理时间过长: {processing_time}秒"

                # 断言: 状态已变为draft
                assert meeting_data["status"] == "draft"

                # 断言: draft stage存在且有内容
                assert "stages" in meeting_data
                assert "draft" in meeting_data["stages"]
                draft_stage = meeting_data["stages"]["draft"]
                assert draft_stage["status"] == "completed"
                assert "content" in draft_stage
                assert len(draft_stage["content"]) > 0

    @pytest.mark.asyncio
    async def test_text_input_meeting_metadata(self, sample_text_content):
        """测试4: 验证文字输入会议的元数据正确"""
        from src.api.main import app
        import asyncio

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 创建文字输入会议
            response = await client.post(
                "/api/v1/meetings",
                data={
                    "input_type": "text",
                    "text_content": sample_text_content,
                },
            )

            meeting_id = response.json()["id"]

            # 获取会议详情
            detail_response = await client.get(f"/api/v1/meetings/{meeting_id}")
            meeting = detail_response.json()

            # 断言: input_type为text
            assert meeting["input_type"] == "text"

            # 断言: 没有audio_key字段或为None
            assert meeting.get("audio_key") is None or "audio_key" not in meeting

            # 断言: 有original_text字段
            assert "original_text" in meeting or "text_content" in meeting

            # 断言: original_text就是用户输入
            original = meeting.get("original_text") or meeting.get("text_content")
            assert original == sample_text_content

            # 断言: 没有transcription相关字段
            assert "transcription_job_id" not in meeting
            assert "transcription_status" not in meeting

    @pytest.mark.asyncio
    async def test_text_input_generates_valid_draft(self, sample_text_content):
        """测试5: 验证生成的draft内容格式正确"""
        from src.api.main import app
        import asyncio

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 创建并等待完成
            response = await client.post(
                "/api/v1/meetings",
                data={
                    "input_type": "text",
                    "text_content": sample_text_content,
                },
            )

            meeting_id = response.json()["id"]

            # 等待draft完成
            for _ in range(30):
                status_response = await client.get(f"/api/v1/meetings/{meeting_id}")
                meeting_data = status_response.json()

                if meeting_data["status"] == "draft":
                    break
                await asyncio.sleep(1)

            # 获取draft内容
            draft_content = meeting_data["stages"]["draft"]["content"]

            # 断言: Draft是Markdown格式
            assert draft_content.startswith("#")

            # 断言: 包含必需的section
            required_sections = [
                "会议基本信息",
                "讨论议题",
                "决策事项",
                "行动项",
            ]
            for section in required_sections:
                assert (
                    section in draft_content
                ), f"Draft缺少必需section: {section}"

            # 断言: 包含原文中的关键信息
            assert "张三" in draft_content
            assert "李四" in draft_content
            assert "王五" in draft_content
            assert "AI推荐功能" in draft_content or "AI功能" in draft_content

    @pytest.mark.asyncio
    async def test_text_input_performance_comparison(self, sample_text_content):
        """测试6: 验证文字输入比音频输入快"""
        from src.api.main import app
        import asyncio

        async with AsyncClient(app=app, base_url="http://test") as client:
            start_time = time.time()

            # 创建文字输入会议
            response = await client.post(
                "/api/v1/meetings",
                data={
                    "input_type": "text",
                    "text_content": sample_text_content,
                },
            )

            meeting_id = response.json()["id"]
            estimated_time = response.json().get("estimated_completion_time", 0)

            # 断言: 预估时间应小于音频处理时间(通常180秒+)
            assert estimated_time < 60, f"文字输入预估时间过长: {estimated_time}秒"

            # 验证实际处理时间
            for _ in range(60):
                status_response = await client.get(f"/api/v1/meetings/{meeting_id}")
                meeting_data = status_response.json()

                if meeting_data["status"] == "draft":
                    break
                await asyncio.sleep(1)

            actual_time = time.time() - start_time

            # 断言: 实际时间应接近预估时间且远小于音频处理时间
            assert (
                actual_time < 60
            ), f"文字输入实际处理时间过长: {actual_time}秒"

    @pytest.mark.asyncio
    async def test_text_input_validation_errors(self):
        """测试7: 验证文字输入的参数验证"""
        from src.api.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 测试: 缺少text_content
            response = await client.post(
                "/api/v1/meetings",
                data={"input_type": "text"},
            )
            assert response.status_code == 400
            assert "text_content" in response.json()["detail"].lower()

            # 测试: text_content为空
            response = await client.post(
                "/api/v1/meetings",
                data={
                    "input_type": "text",
                    "text_content": "",
                },
            )
            assert response.status_code == 400

            # 测试: text_content过短(少于50字符)
            response = await client.post(
                "/api/v1/meetings",
                data={
                    "input_type": "text",
                    "text_content": "太短了",
                },
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_text_input_with_custom_template(self, sample_text_content):
        """测试8: 验证文字输入可以使用自定义模板"""
        from src.api.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 先创建自定义模板
            template_response = await client.post(
                "/api/v1/templates",
                json={
                    "name": "技术评审模板",
                    "structure": {
                        "sections": [
                            {
                                "name": "评审信息",
                                "fields": [
                                    {"key": "title", "label": "评审主题", "required": True},
                                    {"key": "reviewer", "label": "评审人", "required": True},
                                ],
                            },
                            {
                                "name": "评审内容",
                                "fields": [
                                    {"key": "findings", "label": "发现问题", "required": True},
                                    {
                                        "key": "recommendations",
                                        "label": "改进建议",
                                        "required": True,
                                    },
                                ],
                            },
                        ]
                    },
                },
            )

            assert template_response.status_code in [200, 201]
            template_id = template_response.json()["id"]

            # 使用自定义模板创建文字输入会议
            response = await client.post(
                "/api/v1/meetings",
                data={
                    "input_type": "text",
                    "text_content": sample_text_content,
                    "template_id": template_id,
                },
            )

            assert response.status_code == 202
            meeting_id = response.json()["id"]

            # 验证会议使用了指定模板
            detail_response = await client.get(f"/api/v1/meetings/{meeting_id}")
            meeting = detail_response.json()
            assert meeting.get("template_id") == template_id


class TestTextInputEdgeCases:
    """文字输入边界情况测试"""

    @pytest.mark.asyncio
    async def test_very_long_text_input(self):
        """测试: 超长文字输入"""
        from src.api.main import app

        # 生成10000字的测试文本
        long_text = "会议讨论内容。" * 2000  # 约10000字

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/meetings",
                data={
                    "input_type": "text",
                    "text_content": long_text,
                },
            )

            # 应该接受或返回明确的错误
            assert response.status_code in [202, 422]

            if response.status_code == 422:
                # 如果拒绝,应该有清晰的错误信息
                assert "too long" in response.json()["detail"].lower() or "过长" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_text_with_special_characters(self):
        """测试: 包含特殊字符的文字输入"""
        from src.api.main import app

        special_text = """
会议记录 <test@example.com>

讨论内容:
- SQL注入风险: SELECT * FROM users WHERE id='1' OR '1'='1'
- XSS攻击: <script>alert('xss')</script>
- 特殊符号: ~!@#$%^&*()_+-={}[]|:";'<>?,./

决策: 需要加强输入验证 & 输出转义
"""

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/meetings",
                data={
                    "input_type": "text",
                    "text_content": special_text,
                },
            )

            # 应该正确处理,不应该导致错误
            assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_text_input_concurrent_requests(self, sample_text_content):
        """测试: 并发文字输入请求"""
        from src.api.main import app
        import asyncio

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 同时发送10个请求
            tasks = [
                client.post(
                    "/api/v1/meetings",
                    data={
                        "input_type": "text",
                        "text_content": f"{sample_text_content}\n请求编号: {i}",
                    },
                )
                for i in range(10)
            ]

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # 所有请求都应该成功
            success_count = sum(
                1 for r in responses if not isinstance(r, Exception) and r.status_code == 202
            )
            assert success_count == 10, f"只有{success_count}/10个请求成功"


# 运行说明
if __name__ == "__main__":
    print("运行集成测试: test_text_input.py")
    print("命令: pytest tests/integration/test_text_input.py -v")
    print("\n预期结果: 所有测试应该失败,因为实现代码尚未编写")
    print("\nTDD流程:")
    print("1. 运行测试并观察失败原因")
    print("2. 实现最小代码使测试通过")
    print("3. 重构代码并确保测试仍然通过")
