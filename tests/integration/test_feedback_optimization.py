"""
集成测试: 反馈优化流程 (T010)

测试场景: 基于 /Users/umatoratatsu/Documents/AWS/AWS-Handson/specs/001-ai/quickstart.md 场景2

测试流程:
1. 创建一个draft状态的会议记录(使用fixture)
2. 提交用户反馈(标记问题)
3. 触发优化阶段
4. (模拟) Nova Pro根据反馈优化内容
5. 验证final阶段内容改进了标记的问题
6. 验证feedbacks标记为is_resolved=true

关键验证点:
- draft content vs final content的差异
- feedback中的问题是否被修复
- 状态转换: reviewing → optimized → completed

测试策略:
- 使用moto mock AWS Bedrock和S3服务
- 使用pytest-asyncio进行异步测试
- 模拟Nova Pro返回改进后的内容
- 验证工作流状态机转换
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any
from uuid import uuid4

import pytest
import boto3
from httpx import AsyncClient


@pytest.fixture
def draft_meeting_data() -> Dict[str, Any]:
    """
    创建一个包含draft阶段的会议记录数据

    这个会议记录有已知的问题:
    1. 决策事项中"AI功能"应该是"推荐功能"
    2. 行动项缺少王五的任务
    """
    meeting_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    return {
        "id": meeting_id,
        "created_at": now,
        "updated_at": now,
        "status": "reviewing",  # 处于审查阶段
        "input_type": "audio",
        "stages": {
            "draft": {
                "stage_name": "draft",
                "started_at": now,
                "completed_at": now,
                "status": "completed",
                "content": """# 会议记录

## 会议基本信息
- 会议主题: 产品路线图讨论
- 会议日期: 2025-10-01
- 参与者: 张三, 李四, 王五

## 讨论议题
1. Q4功能规划
2. 用户反馈分析
3. 技术债务优先级

## 决策事项
- 决策1: 优先开发AI功能
- 决策2: 延后移动端适配

## 行动项
- [ ] 张三: 完成AI功能PRD (截止日期: 10-08)
- [ ] 李四: 分析用户反馈数据 (截止日期: 10-05)
""",
                "metadata": {
                    "ai_model": "amazon.nova-pro-v1:0",
                    "processing_time_seconds": 45
                }
            },
            "review": {
                "stage_name": "review",
                "started_at": now,
                "completed_at": None,
                "status": "in_progress",
                "feedbacks": []
            }
        },
        "template_id": "default",
        "audio_s3_key": f"audio/{meeting_id}.mp3",
        "transcript_text": "今天我们讨论了产品路线图..."
    }


@pytest.fixture
def user_feedbacks() -> list[Dict[str, Any]]:
    """
    用户提交的反馈数据

    根据quickstart.md场景2:
    1. 决策1应该是"推荐功能"而非"AI功能"
    2. 缺少王五的行动项
    """
    return [
        {
            "feedback_type": "inaccurate",
            "location": "section:决策事项,line:1",
            "comment": "应该是优先开发推荐功能,不是AI功能",
            "severity": "high"
        },
        {
            "feedback_type": "missing",
            "location": "section:行动项",
            "comment": "缺少王五的行动项: 评估技术债务",
            "severity": "medium"
        }
    ]


@pytest.fixture
def optimized_content() -> str:
    """
    Nova Pro优化后的会议记录内容

    这是模拟Bedrock返回的改进后的内容:
    - 修正了"AI功能"为"推荐功能"
    - 添加了王五的行动项
    """
    return """# 会议记录

## 会议基本信息
- 会议主题: 产品路线图讨论
- 会议日期: 2025-10-01
- 参与者: 张三, 李四, 王五

## 讨论议题
1. Q4功能规划
2. 用户反馈分析
3. 技术债务优先级

## 决策事项
- 决策1: 优先开发推荐功能
- 决策2: 延后移动端适配

## 行动项
- [ ] 张三: 完成推荐功能PRD (截止日期: 10-08)
- [ ] 李四: 分析用户反馈数据 (截止日期: 10-05)
- [ ] 王五: 评估技术债务并制定优先级 (截止日期: 10-10)
"""


# ============================================================================
# 集成测试用例
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestFeedbackOptimizationFlow:
    """
    测试反馈优化完整流程

    测试TDD原则: 这个测试必须先编写,并且预期失败
    因为相关的API端点、服务和存储层尚未实现
    """

    async def test_submit_feedback_and_optimize(
        self,
        s3_client,
        test_bucket,
        draft_meeting_data,
        user_feedbacks,
        optimized_content
    ):
        """
        测试场景: 提交反馈并触发优化流程

        步骤:
        1. 在S3中创建一个draft状态的会议记录
        2. 通过API提交用户反馈
        3. 验证会议记录进入优化阶段
        4. 模拟Bedrock返回优化后的内容
        5. 验证final阶段的内容已改进
        6. 验证反馈标记为已解决
        """
        # Step 1: 在S3中保存draft会议记录
        meeting_id = draft_meeting_data["id"]
        s3_client.put_object(
            Bucket=test_bucket,
            Key=f"meetings/{meeting_id}.json",
            Body=json.dumps(draft_meeting_data, ensure_ascii=False),
            ContentType="application/json"
        )

        # Step 2: 通过API提交反馈
        # 注意: 这个测试预期会失败,因为API尚未实现
        from src.api.main import app  # 这将导致ImportError

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/meetings/{meeting_id}/feedback",
                json={"feedbacks": user_feedbacks}
            )

            # 验证API响应
            assert response.status_code == 202
            response_data = response.json()
            assert response_data["message"] == "反馈已提交,优化中..."
            assert response_data["meeting_id"] == meeting_id

        # Step 3: 验证会议记录状态转换到optimizing
        obj = s3_client.get_object(
            Bucket=test_bucket,
            Key=f"meetings/{meeting_id}.json"
        )
        updated_meeting = json.loads(obj["Body"].read())
        assert updated_meeting["status"] == "optimizing"

        # Step 4: 模拟Bedrock优化调用
        # 在实际实现中,这会由WorkflowService触发
        # 这里我们模拟Bedrock返回优化后的内容

        # Step 5: 等待优化完成 (在实际测试中可能需要轮询或使用异步任务)
        # 这里我们直接验证最终状态

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 轮询直到优化完成
            for _ in range(10):
                response = await client.get(f"/api/v1/meetings/{meeting_id}")
                meeting_data = response.json()

                if meeting_data["status"] in ["optimized", "completed"]:
                    break

                # 等待异步处理
                import asyncio
                await asyncio.sleep(0.5)

        # Step 6: 验证final阶段内容已改进
        final_obj = s3_client.get_object(
            Bucket=test_bucket,
            Key=f"meetings/{meeting_id}.json"
        )
        final_meeting = json.loads(final_obj["Body"].read())

        # 验证状态
        assert final_meeting["status"] in ["optimized", "completed"]

        # 验证final阶段存在
        assert "final" in final_meeting["stages"]
        final_stage = final_meeting["stages"]["final"]
        assert final_stage["status"] == "completed"
        assert final_stage["content"] is not None

        # 验证内容改进: "AI功能" -> "推荐功能"
        final_content = final_stage["content"]
        assert "推荐功能" in final_content
        assert "AI功能" not in final_content or final_content.count("AI功能") == 0

        # 验证王五的行动项已添加
        assert "王五" in final_content
        assert "评估技术债务" in final_content

        # Step 7: 验证反馈标记为已解决
        review_stage = final_meeting["stages"]["review"]
        assert "feedbacks" in review_stage

        for feedback in review_stage["feedbacks"]:
            assert feedback["is_resolved"] is True
            assert "resolved_at" in feedback

    async def test_draft_vs_final_content_diff(
        self,
        s3_client,
        test_bucket,
        draft_meeting_data,
        user_feedbacks
    ):
        """
        测试验证: draft和final内容的差异

        验证点:
        - draft内容包含错误("AI功能")
        - final内容修正了错误("推荐功能")
        - final内容添加了缺失信息(王五的行动项)
        """
        meeting_id = draft_meeting_data["id"]

        # 保存draft会议记录
        s3_client.put_object(
            Bucket=test_bucket,
            Key=f"meetings/{meeting_id}.json",
            Body=json.dumps(draft_meeting_data, ensure_ascii=False),
            ContentType="application/json"
        )

        # 这将失败因为API尚未实现
        from src.api.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 获取draft内容
            draft_response = await client.get(
                f"/api/v1/meetings/{meeting_id}/export?stage=draft"
            )
            assert draft_response.status_code == 200
            draft_content = draft_response.text

            # 提交反馈
            await client.post(
                f"/api/v1/meetings/{meeting_id}/feedback",
                json={"feedbacks": user_feedbacks}
            )

            # 等待优化完成
            import asyncio
            await asyncio.sleep(2)

            # 获取final内容
            final_response = await client.get(
                f"/api/v1/meetings/{meeting_id}/export?stage=final"
            )
            assert final_response.status_code == 200
            final_content = final_response.text

            # 验证差异
            # draft包含错误
            assert "AI功能" in draft_content
            assert "王五" not in draft_content or "王五: 评估" not in draft_content

            # final修正了错误
            assert "推荐功能" in final_content
            assert "王五: 评估技术债务" in final_content

    async def test_workflow_state_transitions(
        self,
        s3_client,
        test_bucket,
        draft_meeting_data,
        user_feedbacks
    ):
        """
        测试验证: 工作流状态机转换

        预期状态转换:
        draft → reviewing → optimizing → optimized → completed
        """
        meeting_id = draft_meeting_data["id"]

        # 初始状态: reviewing
        assert draft_meeting_data["status"] == "reviewing"

        s3_client.put_object(
            Bucket=test_bucket,
            Key=f"meetings/{meeting_id}.json",
            Body=json.dumps(draft_meeting_data, ensure_ascii=False),
            ContentType="application/json"
        )

        # 这将失败因为API尚未实现
        from src.api.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 提交反馈后,状态应该变为optimizing
            response = await client.post(
                f"/api/v1/meetings/{meeting_id}/feedback",
                json={"feedbacks": user_feedbacks}
            )
            assert response.status_code == 202

            # 检查状态变化
            status_response = await client.get(f"/api/v1/meetings/{meeting_id}")
            status_data = status_response.json()
            assert status_data["status"] == "optimizing"

            # 等待优化完成
            import asyncio
            for attempt in range(20):
                await asyncio.sleep(0.5)
                status_response = await client.get(f"/api/v1/meetings/{meeting_id}")
                status_data = status_response.json()

                if status_data["status"] in ["optimized", "completed"]:
                    break

            # 最终状态应该是optimized或completed
            assert status_data["status"] in ["optimized", "completed"]

            # 验证阶段完成
            assert status_data["stages"]["draft"]["status"] == "completed"
            assert status_data["stages"]["review"]["status"] == "completed"
            assert status_data["stages"]["final"]["status"] == "completed"

    async def test_feedback_resolution_tracking(
        self,
        s3_client,
        test_bucket,
        draft_meeting_data,
        user_feedbacks
    ):
        """
        测试验证: 反馈解决追踪

        验证点:
        - 每个反馈都有is_resolved标志
        - 优化后is_resolved应该为true
        - 反馈包含resolved_at时间戳
        """
        meeting_id = draft_meeting_data["id"]

        s3_client.put_object(
            Bucket=test_bucket,
            Key=f"meetings/{meeting_id}.json",
            Body=json.dumps(draft_meeting_data, ensure_ascii=False),
            ContentType="application/json"
        )

        # 这将失败因为API尚未实现
        from src.api.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 提交反馈
            response = await client.post(
                f"/api/v1/meetings/{meeting_id}/feedback",
                json={"feedbacks": user_feedbacks}
            )
            assert response.status_code == 202

            # 等待优化完成
            import asyncio
            await asyncio.sleep(2)

            # 获取最终会议记录
            final_response = await client.get(f"/api/v1/meetings/{meeting_id}")
            final_data = final_response.json()

            # 验证反馈解决状态
            review_stage = final_data["stages"]["review"]
            feedbacks = review_stage["feedbacks"]

            assert len(feedbacks) == len(user_feedbacks)

            for feedback in feedbacks:
                # 每个反馈都应该被标记为已解决
                assert "is_resolved" in feedback
                assert feedback["is_resolved"] is True

                # 应该有解决时间戳
                assert "resolved_at" in feedback
                assert feedback["resolved_at"] is not None

                # 应该保留原始反馈信息
                assert "feedback_type" in feedback
                assert "location" in feedback
                assert "comment" in feedback


# ============================================================================
# 边界情况测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestFeedbackOptimizationEdgeCases:
    """测试边界情况和错误处理"""

    async def test_submit_feedback_to_non_reviewing_meeting(
        self,
        s3_client,
        test_bucket
    ):
        """
        测试: 向非reviewing状态的会议提交反馈应该失败

        预期: HTTP 409 Conflict
        """
        meeting_id = str(uuid4())
        meeting_data = {
            "id": meeting_id,
            "status": "completed",  # 已完成的会议
            "stages": {}
        }

        s3_client.put_object(
            Bucket=test_bucket,
            Key=f"meetings/{meeting_id}.json",
            Body=json.dumps(meeting_data),
            ContentType="application/json"
        )

        from src.api.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/meetings/{meeting_id}/feedback",
                json={"feedbacks": [{"feedback_type": "inaccurate", "comment": "test"}]}
            )

            # 应该返回冲突错误
            assert response.status_code == 409
            error_data = response.json()
            assert "不允许反馈" in error_data["detail"] or "conflict" in error_data["detail"].lower()

    async def test_submit_empty_feedback(
        self,
        s3_client,
        test_bucket,
        draft_meeting_data
    ):
        """
        测试: 提交空反馈列表

        预期: 应该跳过优化阶段或返回400错误
        """
        meeting_id = draft_meeting_data["id"]

        s3_client.put_object(
            Bucket=test_bucket,
            Key=f"meetings/{meeting_id}.json",
            Body=json.dumps(draft_meeting_data, ensure_ascii=False),
            ContentType="application/json"
        )

        from src.api.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/meetings/{meeting_id}/feedback",
                json={"feedbacks": []}
            )

            # 可能返回400或202(跳过优化)
            assert response.status_code in [400, 202]

    async def test_feedback_to_nonexistent_meeting(self):
        """
        测试: 向不存在的会议提交反馈

        预期: HTTP 404 Not Found
        """
        from src.api.main import app

        fake_meeting_id = str(uuid4())

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/meetings/{fake_meeting_id}/feedback",
                json={"feedbacks": [{"feedback_type": "missing", "comment": "test"}]}
            )

            assert response.status_code == 404


# ============================================================================
# Mock配置辅助函数
# ============================================================================

def mock_bedrock_invoke_model(model_id: str, body: dict) -> dict:
    """
    模拟Bedrock InvokeModel响应

    根据输入的prompt返回相应的优化内容
    """
    # 这是一个简化的模拟实现
    # 实际测试中会使用moto的mock功能

    if "优化" in str(body) or "feedback" in str(body):
        # 返回优化后的内容
        return {
            "body": json.dumps({
                "completion": """# 会议记录

## 会议基本信息
- 会议主题: 产品路线图讨论
- 会议日期: 2025-10-01
- 参与者: 张三, 李四, 王五

## 讨论议题
1. Q4功能规划
2. 用户反馈分析
3. 技术债务优先级

## 决策事项
- 决策1: 优先开发推荐功能
- 决策2: 延后移动端适配

## 行动项
- [ ] 张三: 完成推荐功能PRD (截止日期: 10-08)
- [ ] 李四: 分析用户反馈数据 (截止日期: 10-05)
- [ ] 王五: 评估技术债务并制定优先级 (截止日期: 10-10)
"""
            })
        }

    return {"body": json.dumps({"completion": "默认响应"})}
