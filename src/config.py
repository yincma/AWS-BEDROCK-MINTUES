"""
应用配置

使用Pydantic Settings管理环境变量配置
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类

    从环境变量读取配置，支持.env文件
    """

    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # S3 Storage
    s3_bucket_name: str = "meeting-minutes-dev"

    # Bedrock Configuration
    bedrock_model_id: str = "amazon.nova-pro-v1:0"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "AWS Bedrock Minutes API"
    api_version: str = "1.0.0"

    # Transcribe Configuration
    transcribe_language_code: str = "zh-CN"

    # Application Settings
    max_audio_size_mb: int = 100
    max_audio_duration_seconds: int = 7200
    supported_audio_formats: str = "mp3,wav,mp4"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例

    使用lru_cache确保配置只加载一次

    Returns:
        Settings实例
    """
    return Settings()
