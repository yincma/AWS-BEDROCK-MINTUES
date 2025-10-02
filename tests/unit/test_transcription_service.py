"""
TranscriptionService单元测试
使用moto模拟AWS服务
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import asyncio

from src.services.transcription_service import (
    TranscriptionService,
    TranscriptionError
)


@pytest.fixture
def transcription_service():
    """创建TranscriptionService实例"""
    return TranscriptionService(
        s3_bucket="test-bucket",
        region="us-east-1",
        output_prefix="transcripts/"
    )


@pytest.fixture
def mock_transcribe_response():
    """模拟Transcribe响应"""
    return {
        'TranscriptionJob': {
            'TranscriptionJobName': 'test-job-123',
            'TranscriptionJobStatus': 'IN_PROGRESS',
            'LanguageCode': 'zh-CN',
            'MediaFormat': 'mp3',
            'Media': {
                'MediaFileUri': 's3://test-bucket/audio/test.mp3'
            }
        }
    }


@pytest.fixture
def mock_completed_job():
    """模拟完成的转录作业"""
    return {
        'TranscriptionJob': {
            'TranscriptionJobName': 'test-job-123',
            'TranscriptionJobStatus': 'COMPLETED',
            'Transcript': {
                'TranscriptFileUri': 'https://s3.us-east-1.amazonaws.com/test-bucket/transcripts/test.json'
            }
        }
    }


@pytest.fixture
def mock_transcript_data():
    """模拟转录结果数据"""
    return {
        "results": {
            "transcripts": [
                {
                    "transcript": "这是一个测试转录文本"
                }
            ],
            "speaker_labels": {
                "segments": [
                    {
                        "speaker_label": "spk_0",
                        "start_time": "0.0",
                        "end_time": "2.5",
                        "items": [
                            {
                                "alternatives": [
                                    {"content": "这是"}
                                ]
                            },
                            {
                                "alternatives": [
                                    {"content": "一个"}
                                ]
                            }
                        ]
                    },
                    {
                        "speaker_label": "spk_1",
                        "start_time": "2.5",
                        "end_time": "5.0",
                        "items": [
                            {
                                "alternatives": [
                                    {"content": "测试"}
                                ]
                            },
                            {
                                "alternatives": [
                                    {"content": "转录文本"}
                                ]
                            }
                        ]
                    }
                ]
            }
        }
    }


class TestTranscriptionService:
    """TranscriptionService测试类"""

    @pytest.mark.asyncio
    async def test_start_transcription_success(self, transcription_service, mock_transcribe_response):
        """测试成功启动转录"""
        with patch.object(transcription_service.transcribe, 'start_transcription_job',
                         return_value=mock_transcribe_response) as mock_start:

            job_id = await transcription_service.start_transcription(
                audio_s3_key="audio/test.mp3",
                language_code="zh-CN"
            )

            assert job_id.startswith("meeting-transcription-")
            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_transcription_with_vocabulary(self, transcription_service, mock_transcribe_response):
        """测试带自定义词汇表的转录"""
        with patch.object(transcription_service.transcribe, 'start_transcription_job',
                         return_value=mock_transcribe_response) as mock_start:

            job_id = await transcription_service.start_transcription(
                audio_s3_key="audio/test.mp3",
                language_code="zh-CN",
                vocabulary_name="custom-vocab"
            )

            assert job_id.startswith("meeting-transcription-")

            # 验证调用参数包含词汇表
            call_args = mock_start.call_args[1]
            assert call_args['Settings']['VocabularyName'] == "custom-vocab"

    @pytest.mark.asyncio
    async def test_start_transcription_rate_limit_retry(self, transcription_service):
        """测试限流重试"""
        from botocore.exceptions import ClientError

        error_response = {
            'Error': {
                'Code': 'LimitExceededException',
                'Message': 'Rate limit exceeded'
            }
        }

        # 第一次调用失败，第二次成功
        with patch.object(transcription_service.transcribe, 'start_transcription_job') as mock_start:
            mock_start.side_effect = [
                ClientError(error_response, 'StartTranscriptionJob'),
                {'TranscriptionJob': {'TranscriptionJobName': 'test-job-123'}}
            ]

            job_id = await transcription_service.start_transcription(
                audio_s3_key="audio/test.mp3"
            )

            assert job_id.startswith("meeting-transcription-")
            assert mock_start.call_count == 2

    @pytest.mark.asyncio
    async def test_wait_for_completion_success(
        self,
        transcription_service,
        mock_completed_job,
        mock_transcript_data
    ):
        """测试成功等待转录完成"""
        # 模拟获取作业状态
        with patch.object(transcription_service.transcribe, 'get_transcription_job',
                         return_value=mock_completed_job):
            # 模拟从S3获取转录结果
            with patch.object(transcription_service.s3, 'get_object') as mock_s3:
                mock_s3.return_value = {
                    'Body': Mock(read=lambda: json.dumps(mock_transcript_data).encode())
                }

                result = await transcription_service.wait_for_completion("test-job-123")

                assert "[spk_0" in result
                assert "[spk_1" in result
                assert "这是 一个" in result
                assert "测试 转录文本" in result

    @pytest.mark.asyncio
    async def test_wait_for_completion_timeout(self, transcription_service):
        """测试转录超时"""
        in_progress_response = {
            'TranscriptionJob': {
                'TranscriptionJobStatus': 'IN_PROGRESS'
            }
        }

        with patch.object(transcription_service.transcribe, 'get_transcription_job',
                         return_value=in_progress_response):

            with pytest.raises(TimeoutError, match="timed out"):
                await transcription_service.wait_for_completion(
                    "test-job-123",
                    max_wait_seconds=1,
                    poll_interval=0.5
                )

    @pytest.mark.asyncio
    async def test_wait_for_completion_failed(self, transcription_service):
        """测试转录失败"""
        failed_response = {
            'TranscriptionJob': {
                'TranscriptionJobStatus': 'FAILED',
                'FailureReason': 'Invalid audio format'
            }
        }

        with patch.object(transcription_service.transcribe, 'get_transcription_job',
                         return_value=failed_response):

            with pytest.raises(TranscriptionError, match="Invalid audio format"):
                await transcription_service.wait_for_completion("test-job-123")

    @pytest.mark.asyncio
    async def test_format_transcript_without_speakers(self, transcription_service):
        """测试格式化没有说话人分离的转录"""
        transcript_data = {
            "results": {
                "transcripts": [
                    {
                        "transcript": "这是一个没有说话人分离的转录文本"
                    }
                ]
            }
        }

        result = transcription_service._format_transcript_with_speakers(transcript_data["results"])
        assert result == "这是一个没有说话人分离的转录文本"

    @pytest.mark.asyncio
    async def test_get_audio_duration(self, transcription_service):
        """测试获取音频时长"""
        mock_response = {
            'Metadata': {
                'duration': '3600'
            }
        }

        with patch.object(transcription_service.s3, 'head_object',
                         return_value=mock_response):

            duration = await transcription_service.get_audio_duration("audio/test.mp3")
            assert duration == 3600

    @pytest.mark.asyncio
    async def test_get_audio_duration_no_metadata(self, transcription_service):
        """测试获取音频时长(无元数据)"""
        mock_response = {
            'Metadata': {}
        }

        with patch.object(transcription_service.s3, 'head_object',
                         return_value=mock_response):

            duration = await transcription_service.get_audio_duration("audio/test.mp3")
            assert duration is None

    @pytest.mark.asyncio
    async def test_cancel_transcription_success(self, transcription_service):
        """测试成功取消转录"""
        with patch.object(transcription_service.transcribe, 'delete_transcription_job') as mock_delete:

            result = await transcription_service.cancel_transcription("test-job-123")

            assert result is True
            mock_delete.assert_called_once_with(TranscriptionJobName="test-job-123")

    @pytest.mark.asyncio
    async def test_cancel_transcription_not_found(self, transcription_service):
        """测试取消不存在的转录作业"""
        from botocore.exceptions import ClientError

        error_response = {
            'Error': {
                'Code': 'BadRequestException',
                'Message': 'Job not found'
            }
        }

        with patch.object(transcription_service.transcribe, 'delete_transcription_job',
                         side_effect=ClientError(error_response, 'DeleteTranscriptionJob')):

            result = await transcription_service.cancel_transcription("test-job-123")
            assert result is False

    def test_generate_job_name(self, transcription_service):
        """测试生成作业名称"""
        job_name = transcription_service._generate_job_name()

        assert job_name.startswith("meeting-transcription-")
        assert len(job_name) > 30  # 包含时间戳和UUID

    def test_build_job_config(self, transcription_service):
        """测试构建作业配置"""
        config = transcription_service._build_job_config(
            job_name="test-job",
            audio_s3_key="audio/test.mp3",
            language_code="zh-CN",
            vocabulary_name="custom-vocab",
            max_speakers=5
        )

        assert config['TranscriptionJobName'] == "test-job"
        assert config['LanguageCode'] == "zh-CN"
        assert config['Media']['MediaFileUri'] == "s3://test-bucket/audio/test.mp3"
        assert config['OutputBucketName'] == "test-bucket"
        assert config['OutputKey'] == "transcripts/test-job.json"
        assert config['Settings']['ShowSpeakerLabels'] is True
        assert config['Settings']['MaxSpeakerLabels'] == 5
        assert config['Settings']['VocabularyName'] == "custom-vocab"