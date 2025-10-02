"""
FastAPI依赖注入工厂函数

提供所有服务层和存储层的依赖注入
"""
from fastapi import Depends

from src.config import Settings, get_settings
from src.services.ai_service import AIService
from src.services.file_service import FileService
from src.services.template_service import TemplateService
from src.services.transcription_service import TranscriptionService
from src.services.workflow_service import WorkflowService
from src.storage.meeting_repository import MeetingRepository
from src.storage.s3_client import S3ClientWrapper
from src.storage.template_repository import TemplateRepository


def get_s3_client(settings: Settings = Depends(get_settings)) -> S3ClientWrapper:
    """获取S3客户端实例"""
    return S3ClientWrapper(
        bucket_name=settings.s3_bucket_name, region=settings.aws_region
    )


def get_meeting_repository(
    s3_client: S3ClientWrapper = Depends(get_s3_client),
) -> MeetingRepository:
    """获取会议记录仓库实例"""
    return MeetingRepository(s3_client)


def get_template_repository(
    s3_client: S3ClientWrapper = Depends(get_s3_client),
) -> TemplateRepository:
    """获取模板仓库实例"""
    return TemplateRepository(s3_client)


def get_transcription_service(
    settings: Settings = Depends(get_settings),
) -> TranscriptionService:
    """获取转录服务实例"""
    return TranscriptionService(
        region=settings.aws_region, s3_bucket=settings.s3_bucket_name
    )


def get_ai_service(settings: Settings = Depends(get_settings)) -> AIService:
    """获取AI服务实例"""
    return AIService(model_id=settings.bedrock_model_id, region=settings.aws_region)


def get_template_service(
    template_repo: TemplateRepository = Depends(get_template_repository),
) -> TemplateService:
    """获取模板服务实例"""
    return TemplateService(template_repo)


def get_file_service(
    s3_client: S3ClientWrapper = Depends(get_s3_client),
    settings: Settings = Depends(get_settings),
) -> FileService:
    """获取文件服务实例"""
    return FileService(s3_client=s3_client, bucket_name=settings.s3_bucket_name)


def get_workflow_service(
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
    template_repo: TemplateRepository = Depends(get_template_repository),
    transcription_service: TranscriptionService = Depends(get_transcription_service),
    ai_service: AIService = Depends(get_ai_service),
) -> WorkflowService:
    """获取工作流服务实例"""
    return WorkflowService(
        meeting_repo=meeting_repo,
        template_repo=template_repo,
        transcription_service=transcription_service,
        ai_service=ai_service,
    )
