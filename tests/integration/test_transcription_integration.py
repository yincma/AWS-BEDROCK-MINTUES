"""
TranscriptionService集成测试
测试与AWS服务的实际集成(使用moto模拟)
"""

import pytest
import json
import asyncio
from unittest.mock import patch, Mock, MagicMock
from moto import mock_aws
import boto3

from src.services.transcription_service import (
    TranscriptionService,
    TranscriptionError
)


@pytest.fixture
def aws_credentials(monkeypatch):
    """设置测试用的AWS凭证"""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "test")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def s3_bucket(aws_credentials):
    """创建测试用的S3 bucket"""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        bucket_name = "test-meeting-bucket"
        s3.create_bucket(Bucket=bucket_name)

        # 上传测试音频文件
        s3.put_object(
            Bucket=bucket_name,
            Key="audio/test-meeting.mp3",
            Body=b"fake audio content",
            Metadata={"duration": "3600"}
        )

        yield bucket_name


class TestTranscriptionIntegration:
    """TranscriptionService集成测试"""

    @pytest.mark.asyncio
    async def test_full_transcription_workflow(self, s3_bucket):
        """测试完整的转录工作流"""
        service = TranscriptionService(
            s3_bucket=s3_bucket,
            region="us-east-1"
        )

        # 模拟Transcribe服务响应
        mock_job_name = "meeting-transcription-test-123"

        # 模拟转录结果
        mock_transcript = {
            "results": {
                "transcripts": [
                    {"transcript": "这是会议的完整转录内容"}
                ],
                "speaker_labels": {
                    "segments": [
                        {
                            "speaker_label": "spk_0",
                            "start_time": "0.0",
                            "end_time": "10.0",
                            "items": [
                                {"alternatives": [{"content": "大家好"}]},
                                {"alternatives": [{"content": "今天"}]},
                                {"alternatives": [{"content": "开会"}]}
                            ]
                        },
                        {
                            "speaker_label": "spk_1",
                            "start_time": "10.0",
                            "end_time": "20.0",
                            "items": [
                                {"alternatives": [{"content": "好的"}]},
                                {"alternatives": [{"content": "我们"}]},
                                {"alternatives": [{"content": "开始"}]}
                            ]
                        }
                    ]
                }
            }
        }

        with patch.object(service.transcribe, 'start_transcription_job') as mock_start:
            mock_start.return_value = {
                'TranscriptionJob': {
                    'TranscriptionJobName': mock_job_name,
                    'TranscriptionJobStatus': 'IN_PROGRESS'
                }
            }

            # 启动转录
            job_id = await service.start_transcription(
                audio_s3_key="audio/test-meeting.mp3",
                language_code="zh-CN"
            )

            assert job_id.startswith("meeting-transcription-")

        # 模拟等待完成
        with patch.object(service.transcribe, 'get_transcription_job') as mock_get:
            # 第一次返回IN_PROGRESS，第二次返回COMPLETED
            mock_get.side_effect = [
                {
                    'TranscriptionJob': {
                        'TranscriptionJobStatus': 'IN_PROGRESS'
                    }
                },
                {
                    'TranscriptionJob': {
                        'TranscriptionJobStatus': 'COMPLETED',
                        'Transcript': {
                            'TranscriptFileUri': f'https://s3.us-east-1.amazonaws.com/{s3_bucket}/transcripts/test.json'
                        }
                    }
                }
            ]

            # 模拟从S3获取转录结果
            with patch.object(service.s3, 'get_object') as mock_s3_get:
                mock_s3_get.return_value = {
                    'Body': Mock(read=lambda: json.dumps(mock_transcript).encode())
                }

                transcript = await service.wait_for_completion(
                    job_id,
                    poll_interval=0.1
                )

                # 验证转录结果格式
                assert "[spk_0" in transcript
                assert "[spk_1" in transcript
                assert "大家好 今天 开会" in transcript
                assert "好的 我们 开始" in transcript

    @pytest.mark.asyncio
    async def test_transcription_with_custom_vocabulary(self, s3_bucket):
        """测试使用自定义词汇表的转录"""
        service = TranscriptionService(
            s3_bucket=s3_bucket,
            region="us-east-1"
        )

        with patch.object(service.transcribe, 'start_transcription_job') as mock_start:
            mock_start.return_value = {
                'TranscriptionJob': {
                    'TranscriptionJobName': 'test-job',
                    'TranscriptionJobStatus': 'IN_PROGRESS'
                }
            }

            job_id = await service.start_transcription(
                audio_s3_key="audio/test-meeting.mp3",
                language_code="en-US",
                vocabulary_name="tech-terms",
                max_speakers=15
            )

            # 验证调用参数
            call_args = mock_start.call_args[1]
            assert call_args['Settings']['VocabularyName'] == "tech-terms"
            assert call_args['Settings']['MaxSpeakerLabels'] == 15
            assert call_args['Settings']['ShowSpeakerLabels'] is True

    @pytest.mark.asyncio
    async def test_error_handling_invalid_audio(self, s3_bucket):
        """测试无效音频文件的错误处理"""
        service = TranscriptionService(
            s3_bucket=s3_bucket,
            region="us-east-1"
        )

        from botocore.exceptions import ClientError

        with patch.object(service.transcribe, 'start_transcription_job') as mock_start:
            mock_start.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'BadRequestException',
                        'Message': 'Invalid audio format'
                    }
                },
                'StartTranscriptionJob'
            )

            with pytest.raises(TranscriptionError, match="Invalid audio format"):
                await service.start_transcription(
                    audio_s3_key="audio/invalid.txt"
                )

    @pytest.mark.asyncio
    async def test_concurrent_transcriptions(self, s3_bucket):
        """测试并发转录多个音频"""
        service = TranscriptionService(
            s3_bucket=s3_bucket,
            region="us-east-1"
        )

        job_ids = []

        with patch.object(service.transcribe, 'start_transcription_job') as mock_start:
            mock_start.side_effect = [
                {'TranscriptionJob': {'TranscriptionJobName': f'job-{i}'}}
                for i in range(3)
            ]

            # 并发启动3个转录作业
            tasks = [
                service.start_transcription(f"audio/meeting-{i}.mp3")
                for i in range(3)
            ]

            job_ids = await asyncio.gather(*tasks)

            assert len(job_ids) == 3
            assert all(job_id.startswith("meeting-transcription-") for job_id in job_ids)

    @pytest.mark.asyncio
    async def test_audio_duration_retrieval(self, s3_bucket):
        """测试获取音频时长"""
        service = TranscriptionService(
            s3_bucket=s3_bucket,
            region="us-east-1"
        )

        # S3已经有带duration元数据的音频文件
        duration = await service.get_audio_duration("audio/test-meeting.mp3")

        assert duration == 3600

    @pytest.mark.asyncio
    async def test_transcription_cancellation(self, s3_bucket):
        """测试取消正在进行的转录"""
        service = TranscriptionService(
            s3_bucket=s3_bucket,
            region="us-east-1"
        )

        with patch.object(service.transcribe, 'delete_transcription_job') as mock_delete:
            result = await service.cancel_transcription("ongoing-job-123")

            assert result is True
            mock_delete.assert_called_once_with(
                TranscriptionJobName="ongoing-job-123"
            )

    @pytest.mark.asyncio
    async def test_transcript_formatting_edge_cases(self, s3_bucket):
        """测试转录格式化的边缘情况"""
        service = TranscriptionService(
            s3_bucket=s3_bucket,
            region="us-east-1"
        )

        # 测试空转录
        empty_transcript = {
            "results": {
                "transcripts": [{"transcript": ""}]
            }
        }
        result = service._format_transcript_with_speakers(empty_transcript["results"])
        assert result == ""

        # 测试只有标点的转录
        punctuation_only = {
            "results": {
                "speaker_labels": {
                    "segments": [
                        {
                            "speaker_label": "spk_0",
                            "start_time": "0.0",
                            "end_time": "1.0",
                            "items": [
                                {"alternatives": [{"content": ","}]},
                                {"alternatives": [{"content": "."}]}
                            ]
                        }
                    ]
                }
            }
        }
        result = service._format_transcript_with_speakers(punctuation_only["results"])
        assert "[spk_0" in result

    @pytest.mark.asyncio
    async def test_long_audio_handling(self, s3_bucket):
        """测试长音频(2小时)的处理"""
        service = TranscriptionService(
            s3_bucket=s3_bucket,
            region="us-east-1"
        )

        # 模拟2小时音频的转录
        with patch.object(service, 'get_audio_duration') as mock_duration:
            mock_duration.return_value = 7200  # 2小时

            duration = await service.get_audio_duration("audio/long-meeting.mp3")
            assert duration == 7200

            # 验证等待时间设置
            with patch.object(service.transcribe, 'get_transcription_job') as mock_get:
                mock_get.return_value = {
                    'TranscriptionJob': {
                        'TranscriptionJobStatus': 'COMPLETED',
                        'Transcript': {
                            'TranscriptFileUri': 'https://s3.amazonaws.com/test/transcript.json'
                        }
                    }
                }

                with patch.object(service.s3, 'get_object') as mock_s3:
                    mock_s3.return_value = {
                        'Body': Mock(read=lambda: b'{"results": {"transcripts": [{"transcript": "long content"}]}}')
                    }

                    # 默认最大等待时间应该足够处理2小时音频
                    result = await service.wait_for_completion("long-job")
                    assert result == "long content"