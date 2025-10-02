"""
API路由简化测试 - 快速提升覆盖率
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException


@pytest.mark.unit
@pytest.mark.asyncio
class TestAPIRoutesSimple:
    """API路由简化测试"""

    async def test_meetings_route_validation(self):
        """测试会议路由参数验证"""
        from src.api.routes.meetings import create_meeting
        from fastapi import UploadFile
        from io import BytesIO

        # Mock依赖
        mock_file_service = AsyncMock()
        mock_meeting_repo = AsyncMock()
        mock_workflow = AsyncMock()
        mock_background = MagicMock()

        # 测试audio模式缺少文件
        with pytest.raises(HTTPException) as exc:
            await create_meeting(
                input_type="audio",
                audio_file=None,
                text_content=None,
                template_id="default",
                background_tasks=mock_background,
                file_service=mock_file_service,
                meeting_repo=mock_meeting_repo,
                workflow_service=mock_workflow
            )

        assert exc.value.status_code == 400
        assert "audio_file" in str(exc.value.detail)

    async def test_meetings_route_text_missing_content(self):
        """测试text模式缺少内容"""
        from src.api.routes.meetings import create_meeting

        mock_file_service = AsyncMock()
        mock_meeting_repo = AsyncMock()
        mock_workflow = AsyncMock()
        mock_background = MagicMock()

        with pytest.raises(HTTPException) as exc:
            await create_meeting(
                input_type="text",
                audio_file=None,
                text_content=None,
                template_id="default",
                background_tasks=mock_background,
                file_service=mock_file_service,
                meeting_repo=mock_meeting_repo,
                workflow_service=mock_workflow
            )

        assert exc.value.status_code == 400
        assert "text_content" in str(exc.value.detail)

    async def test_meetings_route_invalid_input_type(self):
        """测试无效的input_type"""
        from src.api.routes.meetings import create_meeting

        mock_file_service = AsyncMock()
        mock_meeting_repo = AsyncMock()
        mock_workflow = AsyncMock()
        mock_background = MagicMock()

        with pytest.raises(HTTPException) as exc:
            await create_meeting(
                input_type="invalid",
                audio_file=None,
                text_content=None,
                template_id="default",
                background_tasks=mock_background,
                file_service=mock_file_service,
                meeting_repo=mock_meeting_repo,
                workflow_service=mock_workflow
            )

        assert exc.value.status_code == 400

    async def test_get_meeting_not_found(self):
        """测试获取不存在的会议"""
        from src.api.routes.meetings import get_meeting

        mock_repo = AsyncMock()
        mock_repo.get.return_value = None

        with pytest.raises(HTTPException) as exc:
            await get_meeting(
                meeting_id="nonexistent-id",
                meeting_repo=mock_repo
            )

        assert exc.value.status_code == 404

    async def test_export_meeting_not_found(self):
        """测试导出不存在的会议"""
        from src.api.routes.meetings import export_meeting

        mock_repo = AsyncMock()
        mock_repo.get.return_value = None

        with pytest.raises(HTTPException) as exc:
            await export_meeting(
                meeting_id="nonexistent-id",
                stage="draft",
                meeting_repo=mock_repo
            )

        assert exc.value.status_code == 404

    async def test_middleware_error_handler(self):
        """测试错误处理中间件"""
        from src.api.middleware.error_handler import error_handler_middleware
        from fastapi import Request
        from fastapi.responses import JSONResponse

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        mock_request.client = MagicMock(host="127.0.0.1")

        async def failing_call_next(request):
            raise Exception("Test error")

        response = await error_handler_middleware(mock_request, failing_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

    async def test_validation_exception_handler(self):
        """测试验证异常处理器"""
        from src.api.middleware.error_handler import validation_exception_handler
        from fastapi import Request
        from fastapi.exceptions import RequestValidationError

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "POST"

        mock_error = MagicMock(spec=RequestValidationError)
        mock_error.errors.return_value = [
            {"type": "missing", "loc": ["body", "field"], "msg": "Field required"}
        ]

        response = await validation_exception_handler(mock_request, mock_error)

        assert response.status_code == 422

    async def test_config_get_settings(self):
        """测试配置单例获取"""
        from src.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        # 应该返回同一个实例
        assert settings1 is settings2
        assert settings1.aws_region is not None
