"""
AWS Transcribe集成服务
负责音频转文字处理，支持说话人识别(diarization)
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """转录服务异常"""
    pass


class TranscriptionService:
    """AWS Transcribe服务封装"""

    def __init__(
        self,
        s3_bucket: str,
        region: str = "us-east-1",
        output_prefix: str = "transcripts/"
    ):
        """
        初始化Transcribe服务

        Args:
            s3_bucket: S3存储桶名称
            region: AWS区域
            output_prefix: 转录结果在S3中的前缀路径
        """
        self.transcribe = boto3.client('transcribe', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.s3_bucket = s3_bucket
        self.region = region
        self.output_prefix = output_prefix

    def _generate_job_name(self) -> str:
        """生成唯一的转录作业名称"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"meeting-transcription-{timestamp}-{unique_id}"

    def _build_job_config(
        self,
        job_name: str,
        audio_s3_key: str,
        language_code: str,
        vocabulary_name: Optional[str] = None,
        max_speakers: int = 10
    ) -> Dict[str, Any]:
        """
        构建Transcribe作业配置

        Args:
            job_name: 作业名称
            audio_s3_key: S3中的音频文件key
            language_code: 语言代码
            vocabulary_name: 自定义词汇表名称(可选)
            max_speakers: 最大说话人数量

        Returns:
            Transcribe作业配置字典
        """
        config = {
            'TranscriptionJobName': job_name,
            'LanguageCode': language_code,
            'Media': {
                'MediaFileUri': f's3://{self.s3_bucket}/{audio_s3_key}'
            },
            'OutputBucketName': self.s3_bucket,
            'OutputKey': f'{self.output_prefix}{job_name}.json',
            'Settings': {
                'ShowSpeakerLabels': True,  # 开启说话人识别
                'MaxSpeakerLabels': max_speakers
            }
        }

        # 如果有自定义词汇表，添加到配置中
        if vocabulary_name:
            config['Settings']['VocabularyName'] = vocabulary_name

        return config

    async def start_transcription(
        self,
        audio_s3_key: str,
        language_code: str = "zh-CN",
        vocabulary_name: Optional[str] = None,
        max_speakers: int = 10
    ) -> str:
        """
        启动AWS Transcribe异步作业

        Args:
            audio_s3_key: S3中的音频文件key (如 "audio/uuid.mp3")
            language_code: 语言代码 (默认中文)
            vocabulary_name: 自定义词汇表名称(可选)
            max_speakers: 最大说话人数量

        Returns:
            job_id: Transcribe作业ID

        Raises:
            TranscriptionError: 启动转录失败
        """
        job_name = self._generate_job_name()
        config = self._build_job_config(
            job_name=job_name,
            audio_s3_key=audio_s3_key,
            language_code=language_code,
            vocabulary_name=vocabulary_name,
            max_speakers=max_speakers
        )

        try:
            logger.info(f"Starting transcription job: {job_name}")
            logger.debug(f"Job config: {config}")

            # 使用异步执行器运行同步的boto3调用
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.transcribe.start_transcription_job(**config)
            )

            logger.info(f"Transcription job started successfully: {job_name}")
            return job_name

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            # 处理限流
            if error_code == 'LimitExceededException':
                logger.warning(f"Rate limit exceeded, will retry: {error_message}")
                # 指数退避重试
                await asyncio.sleep(2)
                return await self.start_transcription(
                    audio_s3_key=audio_s3_key,
                    language_code=language_code,
                    vocabulary_name=vocabulary_name,
                    max_speakers=max_speakers
                )

            logger.error(f"Failed to start transcription: {error_code} - {error_message}")
            raise TranscriptionError(f"Failed to start transcription: {error_message}")

    async def wait_for_completion(
        self,
        job_id: str,
        max_wait_seconds: int = 7200,  # 2小时
        poll_interval: int = 5  # 轮询间隔(秒)
    ) -> str:
        """
        等待转录完成并获取结果

        Args:
            job_id: Transcribe作业ID
            max_wait_seconds: 最大等待时间(秒)
            poll_interval: 轮询间隔(秒)

        Returns:
            transcript_text: 转录的文本内容(包含说话人标记)

        Raises:
            TimeoutError: 超时
            TranscriptionError: 转录失败
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            # 检查是否超时
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait_seconds:
                logger.error(f"Transcription job {job_id} timed out after {elapsed:.0f} seconds")
                raise TimeoutError(f"Transcription job {job_id} timed out")

            try:
                # 获取作业状态
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.transcribe.get_transcription_job(
                        TranscriptionJobName=job_id
                    )
                )

                job = response['TranscriptionJob']
                status = job['TranscriptionJobStatus']

                logger.debug(f"Job {job_id} status: {status}")

                if status == 'COMPLETED':
                    # 转录完成，获取结果
                    logger.info(f"Transcription job {job_id} completed")
                    transcript_uri = job['Transcript']['TranscriptFileUri']
                    return await self._fetch_and_format_transcript(transcript_uri)

                elif status == 'FAILED':
                    # 转录失败
                    failure_reason = job.get('FailureReason', 'Unknown error')
                    logger.error(f"Transcription job {job_id} failed: {failure_reason}")
                    raise TranscriptionError(f"Transcription failed: {failure_reason}")

                elif status in ['QUEUED', 'IN_PROGRESS']:
                    # 仍在处理中，继续等待
                    logger.debug(f"Job {job_id} is {status}, waiting {poll_interval} seconds...")
                    await asyncio.sleep(poll_interval)

                else:
                    # 未知状态
                    logger.warning(f"Unknown job status: {status}")
                    await asyncio.sleep(poll_interval)

            except ClientError as e:
                error_message = e.response['Error']['Message']
                logger.error(f"Error checking job status: {error_message}")
                raise TranscriptionError(f"Error checking transcription status: {error_message}")

    async def _fetch_and_format_transcript(self, transcript_uri: str) -> str:
        """
        从S3获取转录结果并格式化

        Args:
            transcript_uri: 转录结果的S3 URI

        Returns:
            格式化的转录文本(包含说话人标记)
        """
        try:
            # 从URI中提取bucket和key
            # URI格式: https://s3.region.amazonaws.com/bucket/key
            uri_parts = transcript_uri.replace('https://', '').split('/')
            bucket = uri_parts[1]
            key = '/'.join(uri_parts[2:])

            logger.debug(f"Fetching transcript from S3: bucket={bucket}, key={key}")

            # 从S3获取转录结果JSON
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.s3.get_object(Bucket=bucket, Key=key)
            )

            transcript_data = json.loads(response['Body'].read())

            # 处理说话人分离的结果
            if 'results' in transcript_data:
                return self._format_transcript_with_speakers(transcript_data['results'])
            else:
                # 没有结果
                raise TranscriptionError("No transcription results found")

        except Exception as e:
            logger.error(f"Error fetching transcript: {str(e)}")
            raise TranscriptionError(f"Failed to fetch transcript: {str(e)}")

    def _format_transcript_with_speakers(self, results: Dict[str, Any]) -> str:
        """
        格式化带说话人标记的转录文本

        Args:
            results: Transcribe结果字典

        Returns:
            格式化的文本，包含说话人标记
        """
        # 如果有说话人分离结果
        if 'speaker_labels' in results:
            segments = results['speaker_labels']['segments']
            formatted_lines = []

            for segment in segments:
                speaker = segment['speaker_label']
                start_time = segment['start_time']
                end_time = segment['end_time']

                # 收集该段的所有词
                words = []
                for item in segment.get('items', []):
                    if 'alternatives' in item and item['alternatives']:
                        content = item['alternatives'][0].get('content', '')
                        if content:
                            words.append(content)

                if words:
                    text = ' '.join(words)
                    # 格式: [说话人X - 时间] 内容
                    formatted_lines.append(
                        f"[{speaker} - {float(start_time):.1f}s-{float(end_time):.1f}s] {text}"
                    )

            return '\n'.join(formatted_lines)

        # 没有说话人分离，返回纯文本
        else:
            transcripts = results.get('transcripts', [])
            if transcripts:
                return transcripts[0].get('transcript', '')
            return ''

    async def get_audio_duration(self, audio_s3_key: str) -> Optional[int]:
        """
        获取音频时长(秒) - 可选辅助方法

        Args:
            audio_s3_key: S3中的音频文件key

        Returns:
            音频时长(秒)，如果无法获取返回None
        """
        try:
            # 获取音频文件的元数据
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.s3.head_object(
                    Bucket=self.s3_bucket,
                    Key=audio_s3_key
                )
            )

            # 从元数据中获取时长(如果存储了的话)
            metadata = response.get('Metadata', {})
            duration = metadata.get('duration')

            if duration:
                return int(duration)

            # 如果元数据中没有时长信息，返回None
            # 实际应用中可能需要下载音频并使用音频处理库(如mutagen)来获取时长
            logger.warning(f"No duration metadata found for {audio_s3_key}")
            return None

        except Exception as e:
            logger.error(f"Error getting audio duration: {str(e)}")
            return None

    async def cancel_transcription(self, job_id: str) -> bool:
        """
        取消正在进行的转录作业

        Args:
            job_id: Transcribe作业ID

        Returns:
            是否成功取消
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.transcribe.delete_transcription_job(
                    TranscriptionJobName=job_id
                )
            )
            logger.info(f"Transcription job {job_id} cancelled")
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'BadRequestException':
                # 作业可能已经完成或不存在
                logger.warning(f"Cannot cancel job {job_id}: {e.response['Error']['Message']}")
            else:
                logger.error(f"Error cancelling job {job_id}: {e.response['Error']['Message']}")
            return False