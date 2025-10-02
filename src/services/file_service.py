"""文件上传服务"""
import io
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from mutagen import File as MutagenFile
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.wave import WAVE

from src.storage.s3_client import S3ClientWrapper


class FileService:
    """
    文件上传服务类

    负责音频文件的验证、处理和上传到S3
    """

    # 支持的音频格式映射
    CONTENT_TYPE_MAPPING = {
        'audio/mpeg': 'mp3',
        'audio/mp3': 'mp3',
        'audio/wav': 'wav',
        'audio/wave': 'wav',
        'audio/x-wav': 'wav',
        'video/mp4': 'mp4',
        'audio/mp4': 'mp4',
        'audio/m4a': 'm4a'
    }

    # 支持的音频格式列表
    SUPPORTED_FORMATS = list(CONTENT_TYPE_MAPPING.keys())

    def __init__(self, s3_client: S3ClientWrapper, bucket_name: str):
        """
        初始化文件服务

        Args:
            s3_client: S3客户端封装实例
            bucket_name: S3 bucket名称
        """
        self.s3 = s3_client
        self.bucket = bucket_name
        # 使用s3_client的底层boto3客户端，支持mock
        self.s3_native = s3_client.s3

    async def upload_audio(
        self,
        file_bytes: bytes,
        meeting_id: str,
        content_type: str
    ) -> str:
        """
        上传音频文件到S3

        Args:
            file_bytes: 音频文件字节
            meeting_id: 会议ID(UUID)
            content_type: MIME类型 (audio/mpeg, audio/wav, video/mp4等)

        Returns:
            s3_key: S3对象键 (如 "audio/uuid.mp3")

        Raises:
            ValueError: 文件验证失败
            ClientError: S3上传失败
        """
        # 1. 验证音频格式
        await self.validate_audio_format(content_type)

        # 2. 验证文件大小
        await self.validate_file_size(file_bytes)

        # 3. 获取并验证音频时长
        duration_seconds = await self.get_audio_duration(file_bytes, content_type)
        await self.validate_audio_duration(duration_seconds)

        # 4. 根据content_type确定文件扩展名
        file_extension = self.CONTENT_TYPE_MAPPING.get(content_type.lower(), 'mp3')

        # 5. 构建S3 key: audio/{meeting_id}.{ext}
        s3_key = f"audio/{meeting_id}.{file_extension}"

        # 6. 上传到S3
        try:
            self.s3_native.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=file_bytes,
                ContentType=content_type,
                Metadata={
                    'meeting_id': meeting_id,
                    'duration_seconds': str(duration_seconds)
                }
            )
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise RuntimeError(f"S3上传失败 [{error_code}]: {str(e)}")

        # 7. 返回S3 key
        return s3_key

    async def validate_file_size(self, file_bytes: bytes, max_mb: int = 100) -> None:
        """
        验证文件大小

        Args:
            file_bytes: 文件字节
            max_mb: 最大允许大小(MB)，默认100MB

        Raises:
            ValueError: 文件超过大小限制
        """
        size_mb = len(file_bytes) / (1024 * 1024)
        if size_mb > max_mb:
            raise ValueError(
                f"文件大小{size_mb:.2f}MB超过限制{max_mb}MB"
            )

    async def get_audio_duration(self, file_bytes: bytes, content_type: str) -> int:
        """
        获取音频时长(秒)

        使用mutagen库解析音频元数据

        Args:
            file_bytes: 音频文件字节
            content_type: 文件MIME类型

        Returns:
            duration_seconds: 音频时长(秒)

        Raises:
            ValueError: 无效的音频文件或无法获取时长
        """
        try:
            # 创建内存文件对象
            file_obj = io.BytesIO(file_bytes)

            # 根据content_type选择合适的解析器
            audio = None
            content_type_lower = content_type.lower()

            if 'mp3' in content_type_lower or 'mpeg' in content_type_lower:
                # MP3文件
                audio = MP3(file_obj)
            elif 'mp4' in content_type_lower or 'm4a' in content_type_lower:
                # MP4/M4A文件
                audio = MP4(file_obj)
            elif 'wav' in content_type_lower or 'wave' in content_type_lower:
                # WAV文件
                audio = WAVE(file_obj)
            else:
                # 尝试自动检测
                file_obj.seek(0)  # 重置文件指针
                audio = MutagenFile(file_obj)

            if audio is None:
                raise ValueError(f"无法解析音频文件，格式可能不受支持: {content_type}")

            # 获取音频时长
            if hasattr(audio.info, 'length'):
                duration = audio.info.length
                if duration is None or duration <= 0:
                    raise ValueError("无法获取音频时长，文件可能已损坏")
                return int(duration)
            else:
                raise ValueError("音频文件缺少时长信息")

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"无效的音频文件: {str(e)}")

    async def validate_audio_duration(
        self,
        duration_seconds: int,
        max_seconds: int = 7200
    ) -> None:
        """
        验证音频时长

        Args:
            duration_seconds: 音频时长(秒)
            max_seconds: 最大允许时长(秒)，默认7200秒(2小时)

        Raises:
            ValueError: 音频时长超过限制
        """
        if duration_seconds > max_seconds:
            hours = max_seconds / 3600
            actual_hours = duration_seconds / 3600
            raise ValueError(
                f"音频时长{actual_hours:.2f}小时({duration_seconds}秒)超过限制{hours}小时({max_seconds}秒)"
            )

    async def validate_audio_format(self, content_type: str) -> None:
        """
        验证音频格式

        Args:
            content_type: 文件MIME类型

        Raises:
            ValueError: 不支持的音频格式
        """
        content_type_lower = content_type.lower()
        if content_type_lower not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"不支持的格式{content_type}，仅支持: "
                f"MP3 (audio/mpeg), WAV (audio/wav), MP4 (video/mp4, audio/mp4)"
            )

    async def delete_audio(self, s3_key: str) -> None:
        """
        删除S3中的音频文件

        Args:
            s3_key: S3对象键

        Raises:
            ClientError: S3删除失败
        """
        await self.s3.delete(s3_key)

    async def get_audio_url(
        self,
        s3_key: str,
        expires_in: int = 3600
    ) -> str:
        """
        生成音频文件的预签名URL

        Args:
            s3_key: S3对象键
            expires_in: URL有效期(秒)，默认1小时

        Returns:
            预签名URL

        Raises:
            ClientError: S3操作失败
        """
        try:
            url = self.s3_native.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': s3_key
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise RuntimeError(f"生成预签名URL失败 [{error_code}]: {str(e)}")

    async def get_audio_metadata(self, s3_key: str) -> Optional[dict]:
        """
        获取音频文件的元数据

        Args:
            s3_key: S3对象键

        Returns:
            元数据字典或None(如果文件不存在)
        """
        return await self.s3.get_object_metadata(s3_key)