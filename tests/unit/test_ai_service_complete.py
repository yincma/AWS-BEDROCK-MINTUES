"""
AI Service完整单元测试

测试AIService的所有核心功能，包括提取会议信息和优化反馈
使用mock避免真实AWS调用，提升覆盖率到80%以上
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC
from botocore.exceptions import ClientError

from src.services.ai_service import AIService
from src.models.template_v2 import Template, Section, Field
from src.models.feedback import UserFeedback, FeedbackType


@pytest.mark.unit
class TestAIService:
    """AIService单元测试"""

    @pytest.fixture
    def mock_bedrock_client(self):
        """创建mock的Bedrock客户端"""
        mock_client = MagicMock()
        return mock_client

    @pytest.fixture
    def ai_service(self, mock_bedrock_client):
        """创建AIService实例并注入mock client"""
        with patch("boto3.client", return_value=mock_bedrock_client):
            service = AIService(
                model_id="amazon.nova-pro-v1:0",
                region="us-east-1",
                temperature=0.3,
                max_tokens=4000,
            )
            return service

    @pytest.fixture
    def sample_template(self):
        """创建示例模板"""
        return Template(
            name="标准会议记录",
            description="标准会议记录模板",
            category="meeting",
            sections=[
                Section(
                    name="会议基本信息",
                    level=2,
                    fields=[
                        Field(name="会议主题", description="会议的主题", required=True),
                        Field(name="会议日期", description="会议日期", required=True),
                        Field(name="参与者", description="参与者列表", required=False),
                    ],
                ),
                Section(
                    name="会议内容",
                    level=2,
                    fields=[
                        Field(name="讨论议题", description="讨论的主要议题", required=True),
                        Field(name="决策事项", description="会议决策", required=False),
                    ],
                ),
            ],
            tags=["meeting", "standard"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.fixture
    def mock_bedrock_response(self):
        """创建mock的Bedrock响应"""
        return {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": "# 会议记录\n\n## 会议基本信息\n**会议主题**: Q4产品规划\n**会议日期**: 2025-10-01\n\n## 会议内容\n**讨论议题**:\n- AI功能开发\n- 性能优化"
                        }
                    ]
                }
            },
            "usage": {"inputTokens": 100, "outputTokens": 200, "totalTokens": 300},
        }

    @pytest.fixture
    def sample_feedbacks(self):
        """创建示例反馈列表"""
        from uuid import uuid4
        return [
            UserFeedback(
                id=str(uuid4()),
                created_at=datetime.now(UTC),
                feedback_type=FeedbackType.inaccurate,
                location="section:会议基本信息,line:3",
                comment="会议日期不准确",
                is_resolved=False,
            ),
            UserFeedback(
                id=str(uuid4()),
                created_at=datetime.now(UTC),
                feedback_type=FeedbackType.missing,
                location="section:会议内容,line:10",
                comment="缺少关键决策信息",
                is_resolved=False,
            ),
        ]

    async def test_extract_meeting_info_success(
        self, ai_service, sample_template, mock_bedrock_response
    ):
        """测试成功提取会议信息"""
        # 设置mock响应
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_bedrock_response).encode()
        ai_service.bedrock.invoke_model = MagicMock(
            return_value={"body": mock_response}
        )

        # Mock prompt loader
        mock_template = MagicMock()
        mock_template.render.return_value = "mocked prompt"
        ai_service.prompt_loader.load_template = MagicMock(return_value=mock_template)

        transcript = "这是一次关于Q4产品规划的会议，讨论了AI功能开发和性能优化。"

        result = await ai_service.extract_meeting_info(transcript, sample_template)

        # 验证返回结构
        assert "formatted_markdown" in result
        assert "metadata" in result

        # 验证Markdown内容
        markdown = result["formatted_markdown"]
        assert "# 会议记录" in markdown
        assert "会议主题" in markdown

        # 验证元数据
        metadata = result["metadata"]
        assert metadata["model_id"] == "amazon.nova-pro-v1:0"
        assert metadata["input_tokens"] == 100
        assert metadata["output_tokens"] == 200
        assert metadata["total_tokens"] == 300
        assert "validation" in metadata

    async def test_extract_meeting_info_missing_required_fields(
        self, ai_service, sample_template
    ):
        """测试提取结果缺少必填字段时的验证"""
        # 创建缺少必填字段的响应
        incomplete_response = {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": "# 会议记录\n\n## 会议基本信息\n**参与者**: 张三"
                        }
                    ]
                }
            },
            "usage": {"inputTokens": 50, "outputTokens": 30, "totalTokens": 80},
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(incomplete_response).encode()
        ai_service.bedrock.invoke_model = MagicMock(
            return_value={"body": mock_response}
        )

        mock_template = MagicMock()
        mock_template.render.return_value = "mocked prompt"
        ai_service.prompt_loader.load_template = MagicMock(return_value=mock_template)

        transcript = "简短的会议内容"

        result = await ai_service.extract_meeting_info(transcript, sample_template)

        # 验证validation结果
        validation = result["metadata"]["validation"]
        assert validation["is_valid"] is False
        assert len(validation["missing_fields"]) > 0

    async def test_extract_meeting_info_bedrock_error(
        self, ai_service, sample_template
    ):
        """测试Bedrock API错误"""
        # Mock ClientError
        error_response = {"Error": {"Code": "ThrottlingException", "Message": "Rate limit exceeded"}}
        ai_service.bedrock.invoke_model = MagicMock(
            side_effect=ClientError(error_response, "InvokeModel")
        )

        mock_template = MagicMock()
        mock_template.render.return_value = "mocked prompt"
        ai_service.prompt_loader.load_template = MagicMock(return_value=mock_template)

        transcript = "测试内容"

        with pytest.raises(RuntimeError, match="API rate limit exceeded"):
            await ai_service.extract_meeting_info(transcript, sample_template)

    async def test_optimize_with_feedback_success(
        self, ai_service, sample_template, sample_feedbacks, mock_bedrock_response
    ):
        """测试成功使用反馈优化内容"""
        # 设置mock响应
        optimized_response = {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": "# 会议记录\n\n## 会议基本信息\n**会议主题**: Q4产品规划（已优化）\n**会议日期**: 2025-10-01（已修正）\n\n## 会议内容\n**讨论议题**:\n- AI功能开发\n- 性能优化\n**决策事项**:\n- 优先开发AI功能"
                        }
                    ]
                }
            },
            "usage": {"inputTokens": 150, "outputTokens": 250, "totalTokens": 400},
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(optimized_response).encode()
        ai_service.bedrock.invoke_model = MagicMock(
            return_value={"body": mock_response}
        )

        mock_template = MagicMock()
        mock_template.render.return_value = "mocked prompt"
        ai_service.prompt_loader.load_template = MagicMock(return_value=mock_template)

        original_content = "# 会议记录\n\n## 会议基本信息\n**会议主题**: Q4产品规划"

        result = await ai_service.optimize_with_feedback(
            original_content, sample_feedbacks, sample_template
        )

        # 验证返回结构
        assert "optimized_markdown" in result
        assert "metadata" in result

        # 验证优化后的内容
        markdown = result["optimized_markdown"]
        assert "已优化" in markdown or "已修正" in markdown or len(markdown) > len(original_content)

        # 验证元数据
        metadata = result["metadata"]
        assert metadata["model_id"] == "amazon.nova-pro-v1:0"
        assert metadata["feedback_count"] == 2
        assert "feedback_types" in metadata
        assert FeedbackType.inaccurate.value in metadata["feedback_types"]
        assert FeedbackType.missing.value in metadata["feedback_types"]

    async def test_optimize_with_feedback_single_feedback(
        self, ai_service, sample_template
    ):
        """测试使用单个反馈优化"""
        from uuid import uuid4
        single_feedback = [
            UserFeedback(
                id=str(uuid4()),
                created_at=datetime.now(UTC),
                feedback_type=FeedbackType.improvement,
                location="section:会议内容,line:5",
                comment="需要更详细的描述",
                is_resolved=False,
            )
        ]

        optimized_response = {
            "output": {
                "message": {"content": [{"text": "# 优化后的会议记录\n改进了描述"}]}
            },
            "usage": {"inputTokens": 80, "outputTokens": 120, "totalTokens": 200},
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(optimized_response).encode()
        ai_service.bedrock.invoke_model = MagicMock(
            return_value={"body": mock_response}
        )

        mock_template = MagicMock()
        mock_template.render.return_value = "mocked prompt"
        ai_service.prompt_loader.load_template = MagicMock(return_value=mock_template)

        original_content = "# 会议记录"

        result = await ai_service.optimize_with_feedback(
            original_content, single_feedback, sample_template
        )

        metadata = result["metadata"]
        assert metadata["feedback_count"] == 1
        assert FeedbackType.improvement.value in metadata["feedback_types"]

    async def test_invoke_model_with_custom_parameters(self, ai_service):
        """测试使用自定义参数调用模型"""
        mock_response_data = {
            "output": {"message": {"content": [{"text": "测试响应"}]}},
            "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30},
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode()
        ai_service.bedrock.invoke_model = MagicMock(
            return_value={"body": mock_response}
        )

        result = await ai_service._invoke_model(
            prompt="测试prompt", temperature=0.5, max_tokens=2000
        )

        # 验证调用参数
        call_args = ai_service.bedrock.invoke_model.call_args
        body = json.loads(call_args[1]["body"])

        assert body["inferenceConfig"]["temperature"] == 0.5
        assert body["inferenceConfig"]["maxTokens"] == 2000
        assert body["inferenceConfig"]["topP"] == 0.9

        # 验证响应
        assert result == mock_response_data

    async def test_invoke_model_default_parameters(self, ai_service):
        """测试使用默认参数调用模型"""
        mock_response_data = {
            "output": {"message": {"content": [{"text": "测试响应"}]}},
            "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30},
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode()
        ai_service.bedrock.invoke_model = MagicMock(
            return_value={"body": mock_response}
        )

        result = await ai_service._invoke_model(prompt="测试prompt")

        # 验证使用默认参数
        call_args = ai_service.bedrock.invoke_model.call_args
        body = json.loads(call_args[1]["body"])

        assert body["inferenceConfig"]["temperature"] == 0.3
        assert body["inferenceConfig"]["maxTokens"] == 4000

    async def test_invoke_model_throttling_exception(self, ai_service):
        """测试ThrottlingException错误处理"""
        error_response = {
            "Error": {"Code": "ThrottlingException", "Message": "Too many requests"}
        }
        ai_service.bedrock.invoke_model = MagicMock(
            side_effect=ClientError(error_response, "InvokeModel")
        )

        with pytest.raises(RuntimeError, match="API rate limit exceeded"):
            await ai_service._invoke_model("测试prompt")

    async def test_invoke_model_timeout_exception(self, ai_service):
        """测试ModelTimeoutException错误处理"""
        error_response = {
            "Error": {"Code": "ModelTimeoutException", "Message": "Model timed out"}
        }
        ai_service.bedrock.invoke_model = MagicMock(
            side_effect=ClientError(error_response, "InvokeModel")
        )

        with pytest.raises(RuntimeError, match="Model processing timeout"):
            await ai_service._invoke_model("测试prompt")

    async def test_invoke_model_validation_exception(self, ai_service):
        """测试ValidationException错误处理"""
        error_response = {
            "Error": {"Code": "ValidationException", "Message": "Invalid input"}
        }
        ai_service.bedrock.invoke_model = MagicMock(
            side_effect=ClientError(error_response, "InvokeModel")
        )

        with pytest.raises(ValueError, match="Invalid request parameters"):
            await ai_service._invoke_model("测试prompt")

    async def test_invoke_model_unknown_error(self, ai_service):
        """测试未知错误处理"""
        error_response = {
            "Error": {"Code": "UnknownError", "Message": "Something went wrong"}
        }
        ai_service.bedrock.invoke_model = MagicMock(
            side_effect=ClientError(error_response, "InvokeModel")
        )

        with pytest.raises(ClientError):
            await ai_service._invoke_model("测试prompt")

    def test_extract_content_success(self, ai_service):
        """测试成功提取内容"""
        response = {
            "output": {
                "message": {
                    "content": [
                        {"text": "第一段内容"},
                        {"text": "第二段内容"},
                    ]
                }
            }
        }

        content = ai_service._extract_content(response)
        assert content == "第一段内容\n第二段内容"

    def test_extract_content_single_text(self, ai_service):
        """测试提取单个文本内容"""
        response = {
            "output": {
                "message": {
                    "content": [
                        {"text": "单段内容"},
                    ]
                }
            }
        }

        content = ai_service._extract_content(response)
        assert content == "单段内容"

    def test_extract_content_empty_list(self, ai_service):
        """测试提取空内容列表时使用fallback"""
        response = {
            "output": {
                "message": {
                    "content": []
                }
            }
        }

        content = ai_service._extract_content(response)
        # 空列表会触发fallback，返回output的字符串表示
        assert "message" in content or "content" in content

    def test_extract_content_invalid_format(self, ai_service):
        """测试无效格式的响应使用fallback"""
        response = {"invalid": "structure"}

        # 不应该抛出异常，而是使用fallback返回字符串
        content = ai_service._extract_content(response)
        assert isinstance(content, str)

    def test_extract_content_fallback(self, ai_service):
        """测试备用提取路径"""
        response = {
            "output": {"some": "data"}
        }

        content = ai_service._extract_content(response)
        # fallback会将output转换为字符串
        assert isinstance(content, str)
        assert len(content) > 0

    def test_format_template_structure(self, ai_service, sample_template):
        """测试格式化模板结构"""
        formatted = ai_service._format_template_structure(sample_template)

        # 验证包含章节标题
        assert "## 会议基本信息" in formatted
        assert "## 会议内容" in formatted

        # 验证包含字段
        assert "- 会议主题:" in formatted
        assert "(必填)" in formatted
        assert "- 参与者:" in formatted

    def test_format_template_structure_with_different_levels(self, ai_service):
        """测试格式化不同层级的模板结构"""
        template = Template(
            name="测试模板",
            description="测试",
            category="test",
            sections=[
                Section(
                    name="一级标题",
                    level=1,
                    fields=[Field(name="字段1", description="描述1", required=True)],
                ),
                Section(
                    name="三级标题",
                    level=3,
                    fields=[Field(name="字段2", description="描述2", required=False)],
                ),
            ],
            tags=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        formatted = ai_service._format_template_structure(template)

        # 验证不同层级的标题
        assert "# 一级标题" in formatted
        assert "### 三级标题" in formatted

    def test_validate_output_all_required_present(self, ai_service, sample_template):
        """测试验证输出包含所有必填字段"""
        content = """
# 会议记录

## 会议基本信息
**会议主题**: Q4规划
**会议日期**: 2025-10-01

## 会议内容
**讨论议题**:
- 主题1
- 主题2
"""

        result = ai_service._validate_output(content, sample_template)

        assert result["is_valid"] is True
        assert len(result["missing_fields"]) == 0

    def test_validate_output_missing_required_fields(self, ai_service, sample_template):
        """测试验证输出缺少必填字段"""
        content = """
# 会议记录

## 会议基本信息
**参与者**: 张三、李四
"""

        result = ai_service._validate_output(content, sample_template)

        assert result["is_valid"] is False
        assert len(result["missing_fields"]) > 0
        # 应该包含缺失的必填字段
        missing = result["missing_fields"]
        assert any("会议主题" in field for field in missing)
        assert any("会议日期" in field for field in missing)
        assert any("讨论议题" in field for field in missing)

    async def test_extract_meeting_info_general_exception(
        self, ai_service, sample_template
    ):
        """测试提取会议信息时的一般异常处理"""
        ai_service.bedrock.invoke_model = MagicMock(
            side_effect=Exception("Unexpected error")
        )

        mock_template = MagicMock()
        mock_template.render.return_value = "mocked prompt"
        ai_service.prompt_loader.load_template = MagicMock(return_value=mock_template)

        transcript = "测试内容"

        with pytest.raises(Exception):
            await ai_service.extract_meeting_info(transcript, sample_template)

    async def test_optimize_with_feedback_client_error(
        self, ai_service, sample_template, sample_feedbacks
    ):
        """测试优化反馈时的ClientError处理"""
        error_response = {
            "Error": {"Code": "ServiceError", "Message": "Service unavailable"}
        }
        ai_service.bedrock.invoke_model = MagicMock(
            side_effect=ClientError(error_response, "InvokeModel")
        )

        mock_template = MagicMock()
        mock_template.render.return_value = "mocked prompt"
        ai_service.prompt_loader.load_template = MagicMock(return_value=mock_template)

        original_content = "# 会议记录"

        with pytest.raises(ClientError):
            await ai_service.optimize_with_feedback(
                original_content, sample_feedbacks, sample_template
            )

    async def test_optimize_with_feedback_general_exception(
        self, ai_service, sample_template, sample_feedbacks
    ):
        """测试优化反馈时的一般异常处理"""
        ai_service.bedrock.invoke_model = MagicMock(
            side_effect=Exception("Unexpected error")
        )

        mock_template = MagicMock()
        mock_template.render.return_value = "mocked prompt"
        ai_service.prompt_loader.load_template = MagicMock(return_value=mock_template)

        original_content = "# 会议记录"

        with pytest.raises(Exception):
            await ai_service.optimize_with_feedback(
                original_content, sample_feedbacks, sample_template
            )

    def test_ai_service_initialization(self):
        """测试AIService初始化"""
        with patch("boto3.client") as mock_boto_client:
            mock_client = MagicMock()
            mock_boto_client.return_value = mock_client

            service = AIService(
                model_id="test-model",
                region="us-west-2",
                temperature=0.5,
                max_tokens=2000,
            )

            assert service.model_id == "test-model"
            assert service.temperature == 0.5
            assert service.max_tokens == 2000
            mock_boto_client.assert_called_once_with(
                "bedrock-runtime", region_name="us-west-2"
            )

    def test_ai_service_initialization_failure(self):
        """测试AIService初始化失败"""
        with patch("boto3.client", side_effect=Exception("Connection failed")):
            with pytest.raises(Exception, match="Connection failed"):
                AIService()
