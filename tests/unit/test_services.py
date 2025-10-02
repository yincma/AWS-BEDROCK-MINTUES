"""
服务层单元测试

使用unittest.mock模拟依赖，测试服务层的业务逻辑
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch, call
import io

from src.services.workflow_service import WorkflowService, WorkflowError
from src.services.file_service import FileService
from src.models.meeting import (
    MeetingMinute,
    ProcessingStage,
    ReviewStage,
    ProcessingMetadata,
    TokensUsed,
)
from src.models.feedback import UserFeedback, FeedbackType
from src.models.template import DEFAULT_TEMPLATE


@pytest.mark.unit
class TestWorkflowService:
    """工作流服务单元测试"""

    @pytest.fixture
    def mock_dependencies(self):
        """创建mock依赖"""
        meeting_repo = AsyncMock()
        template_repo = AsyncMock()
        transcription_service = AsyncMock()
        ai_service = AsyncMock()

        # 配置默认返回值
        template_repo.get.return_value = DEFAULT_TEMPLATE
        template_repo.get_default.return_value = DEFAULT_TEMPLATE

        return {
            "meeting_repo": meeting_repo,
            "template_repo": template_repo,
            "transcription_service": transcription_service,
            "ai_service": ai_service,
        }

    @pytest.fixture
    def workflow_service(self, mock_dependencies):
        """创建WorkflowService实例"""
        # 为ai_service添加model_id属性
        mock_dependencies["ai_service"].model_id = "test-model-id"

        return WorkflowService(
            meeting_repo=mock_dependencies["meeting_repo"],
            template_repo=mock_dependencies["template_repo"],
            transcription_service=mock_dependencies["transcription_service"],
            ai_service=mock_dependencies["ai_service"],
            max_retries=3,
            retry_delay=0.01,  # 快速测试
        )

    @pytest.fixture
    def sample_text_meeting(self):
        """创建文本输入的会议记录"""
        meeting_id = str(uuid4())
        now = datetime.now(UTC)

        return MeetingMinute(
            id=meeting_id,
            created_at=now,
            updated_at=now,
            status="draft",
            input_type="text",
            original_text="这是会议的原始文本内容",
            template_id="default",
            current_stage="draft",
            stages={},
        )

    @pytest.fixture
    def sample_audio_meeting(self):
        """创建音频输入的会议记录"""
        meeting_id = str(uuid4())
        now = datetime.now(UTC)

        return MeetingMinute(
            id=meeting_id,
            created_at=now,
            updated_at=now,
            status="draft",
            input_type="audio",
            audio_key=f"audio/{meeting_id}.mp3",
            audio_duration_seconds=3600,
            template_id="default",
            current_stage="draft",
            stages={},
        )

    async def test_execute_draft_stage_text_input(
        self, workflow_service, mock_dependencies, sample_text_meeting
    ):
        """测试文字输入的draft阶段,应跳过转录"""
        # 配置mock返回值
        mock_dependencies["meeting_repo"].get.return_value = sample_text_meeting

        # AI服务返回mock结果
        ai_result = {
            "formatted_markdown": "# 会议记录\n\n## 内容\n测试内容",
            "metadata": {"input_tokens": 100, "output_tokens": 200},
        }
        mock_dependencies["ai_service"].extract_meeting_info.return_value = ai_result

        # 执行draft阶段
        await workflow_service.execute_draft_stage(sample_text_meeting.id)

        # 验证调用顺序
        mock_dependencies["meeting_repo"].get.assert_called_once_with(
            sample_text_meeting.id
        )
        mock_dependencies["template_repo"].get.assert_called_once_with("default")

        # 验证没有调用转录服务（因为是文本输入）
        mock_dependencies["transcription_service"].start_transcription.assert_not_called()

        # 验证调用了AI服务
        mock_dependencies["ai_service"].extract_meeting_info.assert_called_once()
        call_args = mock_dependencies["ai_service"].extract_meeting_info.call_args
        assert call_args[0][0] == "这是会议的原始文本内容"  # transcript
        assert call_args[0][1] == DEFAULT_TEMPLATE  # template

        # 验证保存了会议记录
        assert mock_dependencies["meeting_repo"].save.call_count >= 2  # 至少保存2次

        # 获取最后一次保存的会议对象
        last_save_call = mock_dependencies["meeting_repo"].save.call_args_list[-1]
        saved_meeting = last_save_call[0][0]

        # 验证会议状态
        assert saved_meeting.status == "reviewing"
        assert saved_meeting.current_stage == "draft"
        assert "draft" in saved_meeting.stages
        assert saved_meeting.stages["draft"].status == "completed"
        assert saved_meeting.stages["draft"].content == ai_result["formatted_markdown"]

    async def test_execute_draft_stage_audio_input(
        self, workflow_service, mock_dependencies, sample_audio_meeting
    ):
        """测试音频输入的draft阶段,应执行转录"""
        # 配置mock返回值
        mock_dependencies["meeting_repo"].get.return_value = sample_audio_meeting

        # 转录服务返回mock结果
        job_id = "test-job-123"
        transcript = "这是转录后的文本内容"
        mock_dependencies["transcription_service"].start_transcription.return_value = (
            job_id
        )
        mock_dependencies["transcription_service"].wait_for_completion.return_value = (
            transcript
        )

        # AI服务返回mock结果
        ai_result = {
            "formatted_markdown": "# 会议记录\n\n## 转录内容\n" + transcript,
            "metadata": {"input_tokens": 150, "output_tokens": 250},
        }
        mock_dependencies["ai_service"].extract_meeting_info.return_value = ai_result

        # 执行draft阶段
        await workflow_service.execute_draft_stage(sample_audio_meeting.id)

        # 验证调用了转录服务
        mock_dependencies["transcription_service"].start_transcription.assert_called_once()
        transcribe_call = mock_dependencies[
            "transcription_service"
        ].start_transcription.call_args
        assert transcribe_call[1]["audio_s3_key"] == sample_audio_meeting.audio_key
        assert transcribe_call[1]["language_code"] == "zh-CN"

        # 验证等待转录完成
        mock_dependencies["transcription_service"].wait_for_completion.assert_called_once_with(
            job_id=job_id, max_wait_seconds=7200, poll_interval=5
        )

        # 验证AI使用转录后的文本
        mock_dependencies["ai_service"].extract_meeting_info.assert_called_once()
        ai_call_args = mock_dependencies["ai_service"].extract_meeting_info.call_args
        assert ai_call_args[0][0] == transcript

        # 验证保存了original_text
        save_calls = mock_dependencies["meeting_repo"].save.call_args_list
        # 找到保存original_text的调用
        for call_obj in save_calls:
            meeting = call_obj[0][0]
            if hasattr(meeting, "original_text") and meeting.original_text == transcript:
                break
        else:
            pytest.fail("original_text was not saved")

    async def test_execute_optimization_stage(
        self, workflow_service, mock_dependencies, sample_text_meeting
    ):
        """测试优化阶段"""
        # 准备带有draft内容的会议
        meeting_with_draft = sample_text_meeting
        draft_content = "# 初稿会议记录\n\n## 内容\n初稿内容"
        meeting_with_draft.stages["draft"] = ProcessingStage(
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            status="completed",
            content=draft_content,
            metadata=ProcessingMetadata(
                processing_time_seconds=10.0,
                tokens_used=TokensUsed(input=100, output=200),
                model="test-model",
            ),
        )
        meeting_with_draft.status = "reviewing"

        mock_dependencies["meeting_repo"].get.return_value = meeting_with_draft

        # 准备用户反馈（使用字典而非UserFeedback对象，因为Pydantic会验证）
        from src.models.meeting import UserFeedback as MeetingUserFeedback

        feedbacks = [
            MeetingUserFeedback(
                id=str(uuid4()),
                created_at=datetime.now(UTC),
                feedback_type="inaccurate",
                location="section:内容,line:1",
                comment="这里描述不准确",
                is_resolved=False,
            )
        ]

        # AI优化服务返回结果
        optimized_result = {
            "optimized_markdown": "# 优化后的会议记录\n\n## 内容\n优化后的内容",
            "metadata": {"input_tokens": 200, "output_tokens": 300},
        }
        mock_dependencies["ai_service"].optimize_with_feedback.return_value = (
            optimized_result
        )

        # 执行优化阶段
        await workflow_service.execute_optimization_stage(
            sample_text_meeting.id, feedbacks
        )

        # 验证调用AI优化服务
        mock_dependencies["ai_service"].optimize_with_feedback.assert_called_once()
        optimize_call = mock_dependencies["ai_service"].optimize_with_feedback.call_args
        assert optimize_call[0][0] == draft_content  # draft content
        assert optimize_call[0][1] == feedbacks  # feedbacks
        assert optimize_call[0][2] == DEFAULT_TEMPLATE  # template

        # 验证保存了最终结果
        last_save = mock_dependencies["meeting_repo"].save.call_args_list[-1]
        final_meeting = last_save[0][0]

        assert final_meeting.status == "completed"
        assert final_meeting.current_stage == "final"
        assert "final" in final_meeting.stages
        assert final_meeting.stages["final"].status == "completed"
        assert (
            final_meeting.stages["final"].content == optimized_result["optimized_markdown"]
        )

        # 验证反馈已标记为已解决
        assert "review" in final_meeting.stages
        review_stage = final_meeting.stages["review"]
        assert len(review_stage.feedbacks) == 1
        assert review_stage.feedbacks[0].is_resolved is True

    async def test_handle_stage_failure_transcription_error(
        self, workflow_service, mock_dependencies, sample_audio_meeting
    ):
        """测试转录失败的错误处理"""
        mock_dependencies["meeting_repo"].get.return_value = sample_audio_meeting

        # 模拟转录服务失败
        from src.services.transcription_service import TranscriptionError

        mock_dependencies["transcription_service"].start_transcription.side_effect = (
            TranscriptionError("转录服务不可用")
        )

        # 执行draft阶段应该失败
        with pytest.raises(WorkflowError, match="转录失败"):
            await workflow_service.execute_draft_stage(sample_audio_meeting.id)

        # 验证更新了失败状态
        save_calls = mock_dependencies["meeting_repo"].save.call_args_list
        # 最后一次保存应该是失败状态
        final_save = save_calls[-1]
        failed_meeting = final_save[0][0]
        assert failed_meeting.status == "failed"

    async def test_ai_service_retry_on_failure(
        self, workflow_service, mock_dependencies, sample_text_meeting
    ):
        """测试AI服务失败时的重试机制"""
        mock_dependencies["meeting_repo"].get.return_value = sample_text_meeting

        # 前两次调用失败，第三次成功
        ai_result = {
            "formatted_markdown": "# 会议记录\n\n成功结果",
            "metadata": {"input_tokens": 100, "output_tokens": 200},
        }

        mock_dependencies["ai_service"].extract_meeting_info.side_effect = [
            Exception("临时错误1"),
            Exception("临时错误2"),
            ai_result,  # 第三次成功
        ]

        # 执行draft阶段
        await workflow_service.execute_draft_stage(sample_text_meeting.id)

        # 验证重试了3次
        assert mock_dependencies["ai_service"].extract_meeting_info.call_count == 3

        # 验证最终成功保存
        last_save = mock_dependencies["meeting_repo"].save.call_args_list[-1]
        saved_meeting = last_save[0][0]
        assert saved_meeting.status == "reviewing"
        assert saved_meeting.stages["draft"].status == "completed"

    async def test_ai_service_failure_after_max_retries(
        self, workflow_service, mock_dependencies, sample_text_meeting
    ):
        """测试AI服务重试次数用尽后失败"""
        mock_dependencies["meeting_repo"].get.return_value = sample_text_meeting

        # 所有调用都失败
        mock_dependencies["ai_service"].extract_meeting_info.side_effect = Exception(
            "持续失败"
        )

        # 执行draft阶段应该失败
        with pytest.raises(WorkflowError, match="AI调用失败"):
            await workflow_service.execute_draft_stage(sample_text_meeting.id)

        # 验证重试了max_retries次（3次）
        assert mock_dependencies["ai_service"].extract_meeting_info.call_count == 3

    async def test_can_start_optimization(
        self, workflow_service, mock_dependencies, sample_text_meeting
    ):
        """测试检查是否可以开始优化阶段"""
        # 情况1: draft未完成，不能优化
        meeting_draft_pending = sample_text_meeting
        meeting_draft_pending.status = "draft"
        meeting_draft_pending.stages["draft"] = ProcessingStage(
            started_at=datetime.now(UTC),
            status="processing",
            metadata=ProcessingMetadata(),
        )
        mock_dependencies["meeting_repo"].get.return_value = meeting_draft_pending
        assert await workflow_service.can_start_optimization(sample_text_meeting.id) is False

        # 情况2: draft完成但状态不是reviewing，不能优化
        meeting_wrong_status = sample_text_meeting
        meeting_wrong_status.status = "completed"
        meeting_wrong_status.stages["draft"] = ProcessingStage(
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            status="completed",
            content="内容",
            metadata=ProcessingMetadata(),
        )
        mock_dependencies["meeting_repo"].get.return_value = meeting_wrong_status
        assert await workflow_service.can_start_optimization(sample_text_meeting.id) is False

        # 情况3: draft完成且状态是reviewing，可以优化
        meeting_ready = sample_text_meeting
        meeting_ready.status = "reviewing"
        meeting_ready.stages["draft"] = ProcessingStage(
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            status="completed",
            content="内容",
            metadata=ProcessingMetadata(),
        )
        mock_dependencies["meeting_repo"].get.return_value = meeting_ready
        assert await workflow_service.can_start_optimization(sample_text_meeting.id) is True


@pytest.mark.unit
class TestFileService:
    """文件服务单元测试"""

    @pytest.fixture
    def mock_s3_client(self):
        """创建mock S3客户端"""
        s3_wrapper = MagicMock()
        return s3_wrapper

    @pytest.fixture
    def file_service(self, mock_s3_client):
        """创建FileService实例"""
        return FileService(s3_client=mock_s3_client, bucket_name="test-bucket")

    async def test_validate_file_size_success(self, file_service):
        """测试文件大小验证通过"""
        # 50MB文件
        file_bytes = b"x" * (50 * 1024 * 1024)

        # 应该不抛出异常
        await file_service.validate_file_size(file_bytes, max_mb=100)

    async def test_validate_file_size_failure(self, file_service):
        """测试文件大小验证失败"""
        # 101MB文件
        file_bytes = b"x" * (101 * 1024 * 1024)

        # 应该抛出异常
        with pytest.raises(ValueError, match="文件大小.*超过限制"):
            await file_service.validate_file_size(file_bytes, max_mb=100)

    async def test_validate_audio_duration_success(self, file_service):
        """测试音频时长验证通过"""
        # 1小时音频
        duration_seconds = 3600

        # 应该不抛出异常
        await file_service.validate_audio_duration(duration_seconds, max_seconds=7200)

    async def test_validate_audio_duration_failure(self, file_service):
        """测试音频时长验证失败"""
        # 超过2小时（7201秒）
        duration_seconds = 7201

        # 应该抛出异常
        with pytest.raises(ValueError, match="音频时长.*超过限制"):
            await file_service.validate_audio_duration(duration_seconds, max_seconds=7200)

    async def test_validate_audio_format_success(self, file_service):
        """测试音频格式验证通过"""
        valid_formats = ["audio/mpeg", "audio/mp3", "audio/wav", "video/mp4"]

        for content_type in valid_formats:
            # 应该不抛出异常
            await file_service.validate_audio_format(content_type)

    async def test_validate_audio_format_failure(self, file_service):
        """测试音频格式验证失败"""
        invalid_format = "audio/ogg"

        # 应该抛出异常
        with pytest.raises(ValueError, match="不支持的格式"):
            await file_service.validate_audio_format(invalid_format)

    @patch("src.services.file_service.MP3")
    async def test_get_audio_duration_mp3(self, mock_mp3_class, file_service):
        """测试获取MP3音频时长"""
        # Mock MP3对象
        mock_audio = MagicMock()
        mock_audio.info.length = 3600.5  # 1小时
        mock_mp3_class.return_value = mock_audio

        file_bytes = b"fake mp3 data"
        content_type = "audio/mpeg"

        duration = await file_service.get_audio_duration(file_bytes, content_type)

        assert duration == 3600  # 应该转换为整数

    @patch("src.services.file_service.MP3")
    async def test_get_audio_duration_invalid_file(self, mock_mp3_class, file_service):
        """测试无效音频文件"""
        # Mock MP3抛出异常
        mock_mp3_class.side_effect = Exception("无法解析文件")

        file_bytes = b"invalid data"
        content_type = "audio/mpeg"

        with pytest.raises(ValueError, match="无效的音频文件"):
            await file_service.get_audio_duration(file_bytes, content_type)

    @patch("src.services.file_service.MP3")
    async def test_upload_audio_success(self, mock_mp3_class, file_service):
        """测试上传音频文件成功"""
        # Mock音频时长
        mock_audio = MagicMock()
        mock_audio.info.length = 1800.0  # 30分钟
        mock_mp3_class.return_value = mock_audio

        # Mock S3上传
        file_service.s3_native.put_object = MagicMock()

        meeting_id = str(uuid4())
        file_bytes = b"x" * (10 * 1024 * 1024)  # 10MB
        content_type = "audio/mpeg"

        s3_key = await file_service.upload_audio(file_bytes, meeting_id, content_type)

        # 验证返回的S3 key
        assert s3_key == f"audio/{meeting_id}.mp3"

        # 验证S3上传被调用
        file_service.s3_native.put_object.assert_called_once()
        call_kwargs = file_service.s3_native.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == s3_key
        assert call_kwargs["ContentType"] == content_type

    @patch("src.services.file_service.MP3")
    async def test_upload_audio_file_too_large(self, mock_mp3_class, file_service):
        """测试上传过大的音频文件"""
        # Mock音频时长
        mock_audio = MagicMock()
        mock_audio.info.length = 1800.0
        mock_mp3_class.return_value = mock_audio

        meeting_id = str(uuid4())
        file_bytes = b"x" * (101 * 1024 * 1024)  # 101MB，超过限制
        content_type = "audio/mpeg"

        with pytest.raises(ValueError, match="文件大小.*超过限制"):
            await file_service.upload_audio(file_bytes, meeting_id, content_type)

    @patch("src.services.file_service.MP3")
    async def test_upload_audio_duration_too_long(self, mock_mp3_class, file_service):
        """测试上传时长过长的音频"""
        # Mock音频时长超过2小时
        mock_audio = MagicMock()
        mock_audio.info.length = 7201.0  # 2小时1秒
        mock_mp3_class.return_value = mock_audio

        meeting_id = str(uuid4())
        file_bytes = b"x" * (10 * 1024 * 1024)
        content_type = "audio/mpeg"

        with pytest.raises(ValueError, match="音频时长.*超过限制"):
            await file_service.upload_audio(file_bytes, meeting_id, content_type)
