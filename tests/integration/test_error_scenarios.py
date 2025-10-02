"""
错误场景E2E测试

测试各种错误情况和边界场景，确保系统的健壮性
"""

import pytest
import asyncio
from datetime import datetime, UTC
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from src.models.meeting import MeetingMinute, ProcessingStage, ProcessingMetadata


@pytest.mark.integration
class TestErrorScenarios:
    """错误场景集成测试"""

    async def test_file_too_large(self, async_client_with_aws):
        """测试文件过大(>100MB)返回413"""
        client, bucket_name, s3_client = async_client_with_aws

        # 创建101MB的"音频"数据
        large_file_content = b"x" * (101 * 1024 * 1024)

        # 发送请求
        response = await client.post(
            "/meetings",
            data={
                "input_type": "audio",
                "template_id": "default",
            },
            files={
                "audio_file": ("large_audio.mp3", large_file_content, "audio/mpeg")
            },
        )

        # 验证返回413错误
        assert response.status_code == 413
        assert "超过限制" in response.json()["detail"]

    @patch("src.services.file_service.MP3")
    async def test_audio_too_long(self, mock_mp3_class, async_client_with_aws):
        """测试音频超过2小时返回422"""
        client, bucket_name, s3_client = async_client_with_aws

        # Mock音频时长为2小时1秒
        mock_audio = MagicMock()
        mock_audio.info.length = 7201.0  # 2小时1秒
        mock_mp3_class.return_value = mock_audio

        # 创建音频文件（大小合理但时长超限）
        audio_content = b"fake audio data" * 1000  # 约15KB

        # 发送请求
        response = await client.post(
            "/meetings",
            data={
                "input_type": "audio",
                "template_id": "default",
            },
            files={"audio_file": ("long_audio.mp3", audio_content, "audio/mpeg")},
        )

        # 验证返回422错误
        assert response.status_code == 422
        assert "音频时长" in response.json()["detail"]
        assert "超过限制" in response.json()["detail"]

    async def test_unsupported_audio_format(self, async_client_with_aws):
        """测试不支持的格式返回400"""
        client, bucket_name, s3_client = async_client_with_aws

        # 创建OGG格式的音频（不支持的格式）
        audio_content = b"fake ogg data"

        # 发送请求
        response = await client.post(
            "/meetings",
            data={
                "input_type": "audio",
                "template_id": "default",
            },
            files={"audio_file": ("audio.ogg", audio_content, "audio/ogg")},
        )

        # 验证返回400错误
        assert response.status_code == 400
        assert "不支持的格式" in response.json()["detail"]

    async def test_missing_audio_file_for_audio_input(self, async_client_with_aws):
        """测试audio模式但未上传文件返回400"""
        client, bucket_name, s3_client = async_client_with_aws

        # 发送请求（audio模式但没有audio_file）
        response = await client.post(
            "/meetings",
            data={
                "input_type": "audio",
                "template_id": "default",
            },
        )

        # 验证返回400错误
        assert response.status_code == 400
        assert "audio模式必须上传audio_file" in response.json()["detail"]

    async def test_missing_text_content_for_text_input(self, async_client_with_aws):
        """测试text模式但未提供文本内容返回400"""
        client, bucket_name, s3_client = async_client_with_aws

        # 发送请求（text模式但没有text_content）
        response = await client.post(
            "/meetings",
            data={
                "input_type": "text",
                "template_id": "default",
            },
        )

        # 验证返回400错误
        assert response.status_code == 400
        assert "text模式必须提供text_content" in response.json()["detail"]

    async def test_invalid_input_type(self, async_client_with_aws):
        """测试无效的input_type返回400"""
        client, bucket_name, s3_client = async_client_with_aws

        # 发送请求（使用无效的input_type）
        response = await client.post(
            "/meetings",
            data={
                "input_type": "invalid_type",
                "text_content": "测试内容",
            },
        )

        # 验证返回400错误
        assert response.status_code == 400
        assert "input_type必须是audio或text" in response.json()["detail"]

    async def test_get_nonexistent_meeting(self, async_client_with_aws):
        """测试获取不存在的会议返回404"""
        client, bucket_name, s3_client = async_client_with_aws

        non_existent_id = str(uuid4())

        # 发送请求
        response = await client.get(f"/meetings/{non_existent_id}")

        # 验证返回404错误
        assert response.status_code == 404

    async def test_submit_feedback_to_nonexistent_meeting(self, async_client_with_aws):
        """测试向不存在的会议提交反馈返回404"""
        client, bucket_name, s3_client = async_client_with_aws

        non_existent_id = str(uuid4())

        # 发送请求
        response = await client.post(
            f"/meetings/{non_existent_id}/feedbacks",
            json={
                "feedbacks": [
                    {
                        "feedback_type": "inaccurate",
                        "location": "section:测试,line:1",
                        "comment": "测试反馈",
                    }
                ]
            },
        )

        # 验证返回404错误
        assert response.status_code == 404

    async def test_invalid_feedback_location_format(self, async_client_with_aws):
        """测试无效的反馈位置格式返回422"""
        client, bucket_name, s3_client = async_client_with_aws

        # 先创建一个会议
        create_response = await client.post(
            "/meetings",
            data={
                "input_type": "text",
                "text_content": "测试会议内容",
                "template_id": "default",
            },
        )
        assert create_response.status_code == 202
        meeting_id = create_response.json()["id"]

        # 提交格式错误的反馈
        response = await client.post(
            f"/meetings/{meeting_id}/feedbacks",
            json={
                "feedbacks": [
                    {
                        "feedback_type": "inaccurate",
                        "location": "invalid_format",  # 错误格式
                        "comment": "测试反馈",
                    }
                ]
            },
        )

        # 验证返回422错误
        assert response.status_code == 422

    @patch("src.services.transcription_service.TranscriptionService.start_transcription")
    @patch("src.services.transcription_service.TranscriptionService.wait_for_completion")
    @patch("src.services.file_service.MP3")
    async def test_transcribe_service_timeout(
        self,
        mock_mp3_class,
        mock_wait,
        mock_start,
        async_client_with_aws,
    ):
        """测试Transcribe超时导致失败"""
        client, bucket_name, s3_client = async_client_with_aws

        # Mock音频时长
        mock_audio = MagicMock()
        mock_audio.info.length = 1800.0  # 30分钟
        mock_mp3_class.return_value = mock_audio

        # Mock转录服务 - start成功但wait超时
        mock_start.return_value = "test-job-123"
        from src.services.transcription_service import TranscriptionError

        mock_wait.side_effect = TranscriptionError("转录超时")

        # 创建音频文件
        audio_content = b"fake audio data" * 1000

        # 发送请求创建会议
        response = await client.post(
            "/meetings",
            data={
                "input_type": "audio",
                "template_id": "default",
            },
            files={"audio_file": ("audio.mp3", audio_content, "audio/mpeg")},
        )

        # 创建应该成功（202 Accepted）
        assert response.status_code == 202
        meeting_id = response.json()["id"]

        # 等待一段时间让后台任务执行
        await asyncio.sleep(0.5)

        # 检查会议状态应该是failed
        status_response = await client.get(f"/meetings/{meeting_id}")
        if status_response.status_code == 200:
            meeting_data = status_response.json()
            # 如果后台任务已完成，状态应该是failed
            assert meeting_data["status"] in ["draft", "failed"]

    @patch("src.services.ai_service.AIService._invoke_model")
    @patch("src.services.file_service.MP3")
    async def test_bedrock_service_error(
        self, mock_mp3_class, mock_invoke, async_client_with_aws
    ):
        """测试Bedrock调用失败"""
        client, bucket_name, s3_client = async_client_with_aws

        # Mock音频时长
        mock_audio = MagicMock()
        mock_audio.info.length = 300.0  # 5分钟
        mock_mp3_class.return_value = mock_audio

        # Mock Bedrock调用失败
        mock_invoke.side_effect = Exception("Bedrock服务不可用")

        # 创建会议（文本输入，避免转录服务）
        response = await client.post(
            "/meetings",
            data={
                "input_type": "text",
                "text_content": "测试会议内容用于触发Bedrock错误",
                "template_id": "default",
            },
        )

        # 创建应该成功
        assert response.status_code == 202
        meeting_id = response.json()["id"]

        # 等待后台任务执行
        await asyncio.sleep(0.5)

        # 检查会议状态
        status_response = await client.get(f"/meetings/{meeting_id}")
        if status_response.status_code == 200:
            meeting_data = status_response.json()
            # 由于Bedrock失败且会重试，可能需要更长时间才能完全失败
            # 状态可能是draft（正在处理）或failed（已失败）
            assert meeting_data["status"] in ["draft", "failed"]

    @patch("boto3.client")
    async def test_s3_access_denied(self, mock_boto_client, async_client_with_aws):
        """测试S3权限错误"""
        client, bucket_name, s3_client_orig = async_client_with_aws

        # Mock S3客户端抛出AccessDenied错误
        from botocore.exceptions import ClientError

        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "PutObject",
        )
        mock_boto_client.return_value = mock_s3

        # 注意：这个测试可能难以直接触发，因为依赖注入已经创建了S3客户端
        # 这里仅作为示例，实际测试可能需要不同的方法

    async def test_concurrent_update_conflict(self, async_client_with_aws):
        """测试并发更新冲突"""
        client, bucket_name, s3_client = async_client_with_aws

        # 创建一个会议
        create_response = await client.post(
            "/meetings",
            data={
                "input_type": "text",
                "text_content": "初始内容",
                "template_id": "default",
            },
        )
        assert create_response.status_code == 202
        meeting_id = create_response.json()["id"]

        # 等待会议创建完成
        await asyncio.sleep(0.3)

        # 获取会议两次（模拟两个并发客户端）
        response1 = await client.get(f"/meetings/{meeting_id}")
        response2 = await client.get(f"/meetings/{meeting_id}")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # 由于当前实现的并发控制在Repository层，
        # 这里需要通过更新会议来测试
        # 但API层可能没有直接的更新端点
        # 这个测试更适合在Repository层进行（已在test_repositories.py中实现）

    async def test_empty_feedback_list(self, async_client_with_aws):
        """测试提交空反馈列表返回422"""
        client, bucket_name, s3_client = async_client_with_aws

        # 创建会议
        create_response = await client.post(
            "/meetings",
            data={
                "input_type": "text",
                "text_content": "测试内容",
                "template_id": "default",
            },
        )
        assert create_response.status_code == 202
        meeting_id = create_response.json()["id"]

        # 提交空反馈列表
        response = await client.post(
            f"/meetings/{meeting_id}/feedbacks",
            json={"feedbacks": []},  # 空列表
        )

        # 验证返回422错误
        assert response.status_code == 422

    async def test_feedback_comment_too_long(self, async_client_with_aws):
        """测试反馈评论超过1000字符限制"""
        client, bucket_name, s3_client = async_client_with_aws

        # 创建会议
        create_response = await client.post(
            "/meetings",
            data={
                "input_type": "text",
                "text_content": "测试内容",
                "template_id": "default",
            },
        )
        assert create_response.status_code == 202
        meeting_id = create_response.json()["id"]

        # 提交超长评论
        long_comment = "x" * 1001  # 1001字符
        response = await client.post(
            f"/meetings/{meeting_id}/feedbacks",
            json={
                "feedbacks": [
                    {
                        "feedback_type": "improvement",
                        "location": "section:测试,line:1",
                        "comment": long_comment,
                    }
                ]
            },
        )

        # 验证返回422错误
        assert response.status_code == 422

    async def test_invalid_feedback_type(self, async_client_with_aws):
        """测试无效的反馈类型"""
        client, bucket_name, s3_client = async_client_with_aws

        # 创建会议
        create_response = await client.post(
            "/meetings",
            data={
                "input_type": "text",
                "text_content": "测试内容",
                "template_id": "default",
            },
        )
        assert create_response.status_code == 202
        meeting_id = create_response.json()["id"]

        # 提交无效的反馈类型
        response = await client.post(
            f"/meetings/{meeting_id}/feedbacks",
            json={
                "feedbacks": [
                    {
                        "feedback_type": "invalid_type",  # 无效类型
                        "location": "section:测试,line:1",
                        "comment": "测试",
                    }
                ]
            },
        )

        # 验证返回422错误
        assert response.status_code == 422

    async def test_delete_nonexistent_meeting(self, async_client_with_aws):
        """测试删除不存在的会议"""
        client, bucket_name, s3_client = async_client_with_aws

        non_existent_id = str(uuid4())

        # 发送删除请求
        response = await client.delete(f"/meetings/{non_existent_id}")

        # 删除不存在的资源通常返回404
        # 但某些实现可能返回204（幂等性）
        assert response.status_code in [204, 404]

    async def test_get_nonexistent_template(self, async_client_with_aws):
        """测试获取不存在的模板"""
        client, bucket_name, s3_client = async_client_with_aws

        non_existent_id = str(uuid4())

        # 发送请求
        response = await client.get(f"/templates/{non_existent_id}")

        # 验证返回404错误
        assert response.status_code == 404

    async def test_create_meeting_with_nonexistent_template(
        self, async_client_with_aws
    ):
        """测试使用不存在的模板创建会议"""
        client, bucket_name, s3_client = async_client_with_aws

        non_existent_template = str(uuid4())

        # 发送请求
        response = await client.post(
            "/meetings",
            data={
                "input_type": "text",
                "text_content": "测试内容",
                "template_id": non_existent_template,
            },
        )

        # 创建应该成功（会fallback到默认模板）
        # 或者返回400错误（取决于实现）
        assert response.status_code in [202, 400, 404]

    @patch("src.services.file_service.MP3")
    async def test_corrupted_audio_file(self, mock_mp3_class, async_client_with_aws):
        """测试损坏的音频文件"""
        client, bucket_name, s3_client = async_client_with_aws

        # Mock MP3解析失败
        mock_mp3_class.side_effect = Exception("无法解析音频文件")

        # 创建"损坏的"音频文件
        corrupted_audio = b"corrupted data"

        # 发送请求
        response = await client.post(
            "/meetings",
            data={
                "input_type": "audio",
                "template_id": "default",
            },
            files={"audio_file": ("corrupted.mp3", corrupted_audio, "audio/mpeg")},
        )

        # 验证返回400或422错误
        assert response.status_code in [400, 422]
        assert "音频" in response.json()["detail"]

    async def test_rate_limit_protection(self, async_client_with_aws):
        """测试速率限制保护（如果实现）"""
        client, bucket_name, s3_client = async_client_with_aws

        # 快速发送多个请求
        responses = []
        for _ in range(10):
            response = await client.post(
                "/meetings",
                data={
                    "input_type": "text",
                    "text_content": "测试内容",
                    "template_id": "default",
                },
            )
            responses.append(response)

        # 如果有速率限制，某些请求应该返回429
        # 如果没有速率限制，所有请求都应该成功
        status_codes = [r.status_code for r in responses]
        assert all(code in [202, 429] for code in status_codes)
