"""
会议记录相关的API端点

提供会议记录的CRUD操作和工作流控制
"""
import logging
import uuid
from datetime import datetime, UTC
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import PlainTextResponse

from src.api.dependencies import (
    get_file_service,
    get_meeting_repository,
    get_workflow_service,
)
from src.models.feedback import FeedbackBatch, create_feedback_from_input
from src.models.meeting import MeetingMinute, ProcessingStage
from src.services.file_service import FileService
from src.services.workflow_service import WorkflowService
from src.storage.meeting_repository import MeetingRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/meetings", status_code=202)
async def create_meeting(
    input_type: str = Form(...),
    audio_file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None),
    template_id: Optional[str] = Form("default"),
    background_tasks: BackgroundTasks = None,
    file_service: FileService = Depends(get_file_service),
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """创建新会议记录(制作阶段)

    根据输入类型(audio/text)创建会议记录，并在后台启动draft阶段处理。

    Args:
        input_type: 输入类型，必须是"audio"或"text"
        audio_file: 音频文件(当input_type=audio时必需)
        text_content: 文本内容(当input_type=text时必需)
        template_id: 模板ID(可选，默认"default")
        background_tasks: FastAPI后台任务
        file_service: 文件服务(依赖注入)
        meeting_repo: 会议记录仓库(依赖注入)
        workflow_service: 工作流服务(依赖注入)

    Returns:
        会议记录创建响应，包含ID、状态和预估完成时间

    Raises:
        HTTPException 400: 输入验证失败
        HTTPException 413: 文件过大
        HTTPException 422: 音频时长超限
    """
    # 1. 验证input_type
    if input_type not in ["audio", "text"]:
        raise HTTPException(status_code=400, detail="input_type必须是audio或text")

    # 2. 验证对应的输入存在并处理
    duration = None
    audio_key = None
    original_text = None

    if input_type == "audio":
        if not audio_file:
            raise HTTPException(
                status_code=400, detail="audio模式必须上传audio_file"
            )

        # 读取文件
        try:
            file_bytes = await audio_file.read()
        except Exception as e:
            logger.error(f"Failed to read uploaded file: {e}")
            raise HTTPException(status_code=400, detail="无法读取上传的文件")

        # 验证文件大小
        try:
            await file_service.validate_file_size(file_bytes, max_mb=100)
        except ValueError as e:
            raise HTTPException(status_code=413, detail=str(e))

        # 验证音频格式
        try:
            await file_service.validate_audio_format(audio_file.content_type)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # 获取时长
        try:
            duration = await file_service.get_audio_duration(
                file_bytes, audio_file.content_type
            )
            await file_service.validate_audio_duration(duration, max_seconds=7200)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    elif input_type == "text":
        if not text_content:
            raise HTTPException(status_code=400, detail="text模式必须提供text_content")
        original_text = text_content

    # 3. 生成meeting_id和时间戳
    meeting_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    # 4. 如果是音频，先上传到S3获取audio_key
    if input_type == "audio":
        try:
            audio_key = await file_service.upload_audio(
                file_bytes, meeting_id, audio_file.content_type
            )
        except Exception as e:
            logger.error(f"Failed to upload audio: {e}")
            raise HTTPException(status_code=500, detail="音频上传失败")

        # 创建带audio信息的meeting记录
        meeting = MeetingMinute(
            id=meeting_id,
            created_at=now,
            updated_at=now,
            status="draft",
            input_type=input_type,
            template_id=template_id or "default",
            current_stage="draft",
            stages={},
            audio_key=audio_key,
            audio_duration_seconds=duration,
        )
    else:
        # 创建带文本内容的meeting记录
        meeting = MeetingMinute(
            id=meeting_id,
            created_at=now,
            updated_at=now,
            status="draft",
            input_type=input_type,
            template_id=template_id or "default",
            current_stage="draft",
            stages={},
            original_text=original_text,
        )

    # 5. 保存meeting
    try:
        await meeting_repo.save(meeting)
    except Exception as e:
        logger.error(f"Failed to save meeting: {e}")
        raise HTTPException(status_code=500, detail="保存会议记录失败")

    # 6. 后台任务: 执行draft阶段
    background_tasks.add_task(workflow_service.execute_draft_stage, meeting_id)

    # 7. 计算预估完成时间
    if input_type == "audio":
        # 音频: 转录时间 + AI处理时间
        estimated_time = int(duration * 1.5)  # 1.5倍音频时长
    else:
        # 文字: 仅AI处理时间
        estimated_time = 60  # 约1分钟

    # 8. 返回202响应
    return {
        "id": meeting_id,
        "status": "draft",
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "estimated_completion_time": estimated_time,
    }


@router.get("/meetings/{meeting_id}")
async def get_meeting(
    meeting_id: str, meeting_repo: MeetingRepository = Depends(get_meeting_repository)
):
    """获取会议记录详情

    返回会议记录的完整信息，包括所有阶段的处理状态和内容。

    Args:
        meeting_id: 会议记录ID(UUID)
        meeting_repo: 会议记录仓库(依赖注入)

    Returns:
        会议记录完整信息

    Raises:
        HTTPException 404: 会议记录不存在
    """
    meeting = await meeting_repo.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail=f"会议 {meeting_id} 不存在")

    # 返回完整的meeting对象
    return meeting.model_dump(mode="json")


@router.post("/meetings/{meeting_id}/feedback", status_code=202)
async def submit_feedback(
    meeting_id: str,
    feedback_batch: FeedbackBatch,
    background_tasks: BackgroundTasks,
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """提交审查反馈,触发优化阶段

    接收用户对draft版本的反馈，并在后台启动优化阶段生成final版本。

    Args:
        meeting_id: 会议记录ID(UUID)
        feedback_batch: 反馈批次，包含多个反馈项
        background_tasks: FastAPI后台任务
        meeting_repo: 会议记录仓库(依赖注入)
        workflow_service: 工作流服务(依赖注入)

    Returns:
        反馈提交确认信息

    Raises:
        HTTPException 404: 会议记录不存在
        HTTPException 409: 会议状态不允许提交反馈
    """
    meeting = await meeting_repo.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    # 验证状态
    if meeting.status != "reviewing":
        raise HTTPException(
            status_code=409, detail=f"会议状态{meeting.status}不允许提交反馈"
        )

    # 转换FeedbackInput为UserFeedback
    user_feedbacks = [
        create_feedback_from_input(fb) for fb in feedback_batch.feedbacks
    ]

    # 后台任务: 执行优化阶段
    background_tasks.add_task(
        workflow_service.execute_optimization_stage, meeting_id, user_feedbacks
    )

    return {"message": "反馈已提交,优化中...", "meeting_id": meeting_id}


@router.get("/meetings/{meeting_id}/export")
async def export_meeting(
    meeting_id: str,
    stage: str = "final",
    meeting_repo: MeetingRepository = Depends(get_meeting_repository),
):
    """导出会议记录为Markdown

    导出指定阶段的会议记录内容为Markdown格式。

    Args:
        meeting_id: 会议记录ID(UUID)
        stage: 导出哪个阶段的版本，可选值: draft/review/final，默认final
        meeting_repo: 会议记录仓库(依赖注入)

    Returns:
        Markdown格式的会议记录内容

    Raises:
        HTTPException 404: 会议记录不存在或指定阶段不存在
    """
    meeting = await meeting_repo.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    if stage not in meeting.stages:
        raise HTTPException(status_code=404, detail=f"阶段{stage}不存在")

    stage_obj = meeting.stages[stage]

    # 只有ProcessingStage有content字段
    if isinstance(stage_obj, ProcessingStage):
        if not stage_obj.content:
            raise HTTPException(status_code=404, detail=f"阶段{stage}内容不存在")
        content = stage_obj.content
    else:
        # ReviewStage没有content
        raise HTTPException(status_code=404, detail=f"阶段{stage}不支持导出")

    return PlainTextResponse(content=content, media_type="text/markdown")
