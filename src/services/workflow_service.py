"""
三阶段工作流编排服务

负责编排"制作-审查-优化"三阶段工作流，是系统的核心业务逻辑层。
遵循SOLID原则，仅负责编排，具体实现委托给各专用服务。
"""

import asyncio
import logging
from datetime import datetime, UTC
from typing import Optional

from ..models.meeting import (
    MeetingMinute,
    ProcessingStage,
    ReviewStage,
    ProcessingMetadata,
    TokensUsed,
    UserFeedback,
)
from ..models.template import Template
from ..storage.meeting_repository import MeetingRepository
from ..storage.template_repository import TemplateRepository
from .transcription_service import TranscriptionService, TranscriptionError
from .ai_service import AIService

logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """工作流执行异常"""
    pass


class WorkflowService:
    """
    工作流编排服务

    核心职责:
    1. 编排三阶段工作流(draft -> review -> final)
    2. 管理状态机转换
    3. 协调各服务调用
    4. 处理错误和重试
    """

    def __init__(
        self,
        meeting_repo: MeetingRepository,
        template_repo: TemplateRepository,
        transcription_service: TranscriptionService,
        ai_service: AIService,
        max_retries: int = 3,
        retry_delay: int = 2
    ):
        """
        初始化工作流服务

        Args:
            meeting_repo: 会议记录仓库
            template_repo: 模板仓库
            transcription_service: 转录服务
            ai_service: AI服务
            max_retries: AI调用最大重试次数
            retry_delay: 重试间隔(秒)
        """
        self.meeting_repo = meeting_repo
        self.template_repo = template_repo
        self.transcription = transcription_service
        self.ai = ai_service
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def execute_draft_stage(self, meeting_id: str) -> None:
        """
        执行制作阶段工作流

        流程:
        1. 从S3加载meeting记录
        2. 判断input_type并执行转录(如果需要)
        3. 将转录/文本保存到meeting.original_text
        4. 加载template
        5. 调用AI提取会议信息
        6. 渲染Markdown并创建draft阶段
        7. 更新meeting状态为"reviewing"
        8. 保存回S3

        Args:
            meeting_id: 会议记录ID

        Raises:
            WorkflowError: 工作流执行失败
        """
        stage_start_time = datetime.now(UTC)

        try:
            logger.info(f"Starting draft stage for meeting {meeting_id}")

            # 1. 加载meeting记录
            meeting = await self.meeting_repo.get(meeting_id)
            if not meeting:
                raise WorkflowError(f"Meeting {meeting_id} not found")

            # 初始化draft stage
            meeting.stages['draft'] = ProcessingStage(
                started_at=stage_start_time,
                status="processing"
            )
            await self.meeting_repo.save(meeting)

            # 2. 获取转录文本
            transcript = await self._get_or_create_transcript(meeting)

            # 保存转录文本
            meeting.original_text = transcript
            await self.meeting_repo.save(meeting)

            # 3. 加载template
            template = await self._load_template(meeting.template_id)

            # 4. 调用AI提取信息(带重试)
            ai_result = await self._call_ai_with_retry(
                self.ai.extract_meeting_info,
                transcript,
                template
            )

            # 5. 计算处理时间
            stage_end_time = datetime.now(UTC)
            processing_time = (stage_end_time - stage_start_time).total_seconds()

            # 6. 创建ProcessingStage(draft)
            draft_stage = ProcessingStage(
                started_at=stage_start_time,
                completed_at=stage_end_time,
                status="completed",
                content=ai_result['formatted_markdown'],
                metadata=ProcessingMetadata(
                    processing_time_seconds=processing_time,
                    tokens_used=TokensUsed(
                        input=ai_result['metadata'].get('input_tokens', 0),
                        output=ai_result['metadata'].get('output_tokens', 0)
                    ),
                    model=self.ai.model_id
                )
            )

            # 7. 更新meeting状态
            meeting.stages['draft'] = draft_stage
            meeting.status = "reviewing"
            meeting.current_stage = "draft"
            meeting.updated_at = stage_end_time

            # 8. 保存回S3
            await self.meeting_repo.save(meeting)

            logger.info(
                f"Draft stage completed for meeting {meeting_id} "
                f"in {processing_time:.2f} seconds"
            )

        except TranscriptionError as e:
            logger.error(f"Transcription failed for meeting {meeting_id}: {e}")
            await self._handle_stage_failure(meeting_id, "draft", e)
            raise WorkflowError(f"转录失败: {str(e)}") from e

        except Exception as e:
            logger.error(f"Draft stage failed for meeting {meeting_id}: {e}")
            await self._handle_stage_failure(meeting_id, "draft", e)
            raise WorkflowError(f"制作阶段失败: {str(e)}") from e

    async def execute_optimization_stage(
        self,
        meeting_id: str,
        feedbacks: list[UserFeedback]
    ) -> None:
        """
        执行优化阶段工作流

        流程:
        1. 从S3加载meeting
        2. 获取draft阶段的content
        3. 创建ReviewStage保存feedbacks
        4. 调用AI根据反馈优化
        5. 创建final阶段
        6. 标记所有feedbacks为已解决
        7. 更新状态为"completed"
        8. 保存回S3

        Args:
            meeting_id: 会议记录ID
            feedbacks: 用户反馈列表

        Raises:
            WorkflowError: 工作流执行失败
        """
        stage_start_time = datetime.now(UTC)

        try:
            logger.info(
                f"Starting optimization stage for meeting {meeting_id} "
                f"with {len(feedbacks)} feedbacks"
            )

            # 1. 加载meeting
            meeting = await self.meeting_repo.get(meeting_id)
            if not meeting:
                raise WorkflowError(f"Meeting {meeting_id} not found")

            # 2. 验证draft阶段存在
            if 'draft' not in meeting.stages:
                raise WorkflowError("Draft stage not found, cannot optimize")

            draft_stage = meeting.stages['draft']
            if not isinstance(draft_stage, ProcessingStage):
                raise WorkflowError("Invalid draft stage data")

            if not draft_stage.content:
                raise WorkflowError("Draft content is empty")

            # 3. 创建ReviewStage
            review_stage = ReviewStage(
                started_at=stage_start_time,
                completed_at=datetime.now(UTC),
                feedbacks=feedbacks
            )
            meeting.stages['review'] = review_stage
            meeting.current_stage = "review"
            await self.meeting_repo.save(meeting)

            # 4. 加载template
            template = await self._load_template(meeting.template_id)

            # 5. 调用AI优化(带重试)
            ai_result = await self._call_ai_with_retry(
                self.ai.optimize_with_feedback,
                draft_stage.content,
                feedbacks,
                template
            )

            # 6. 计算处理时间
            stage_end_time = datetime.now(UTC)
            processing_time = (stage_end_time - stage_start_time).total_seconds()

            # 7. 创建ProcessingStage(final)
            final_stage = ProcessingStage(
                started_at=stage_start_time,
                completed_at=stage_end_time,
                status="completed",
                content=ai_result['optimized_markdown'],
                metadata=ProcessingMetadata(
                    processing_time_seconds=processing_time,
                    tokens_used=TokensUsed(
                        input=ai_result['metadata'].get('input_tokens', 0),
                        output=ai_result['metadata'].get('output_tokens', 0)
                    ),
                    model=self.ai.model_id
                )
            )

            # 8. 标记所有feedbacks为已解决
            for feedback in feedbacks:
                feedback.is_resolved = True

            # 更新review_stage中的feedbacks
            review_stage.feedbacks = feedbacks
            review_stage.completed_at = stage_end_time

            # 9. 更新meeting状态
            meeting.stages['final'] = final_stage
            meeting.stages['review'] = review_stage
            meeting.status = "completed"
            meeting.current_stage = "final"
            meeting.updated_at = stage_end_time

            # 10. 保存回S3
            await self.meeting_repo.save(meeting)

            logger.info(
                f"Optimization stage completed for meeting {meeting_id} "
                f"in {processing_time:.2f} seconds"
            )

        except Exception as e:
            logger.error(f"Optimization stage failed for meeting {meeting_id}: {e}")
            await self._handle_stage_failure(meeting_id, "final", e)
            raise WorkflowError(f"优化阶段失败: {str(e)}") from e

    async def _get_or_create_transcript(self, meeting: MeetingMinute) -> str:
        """
        获取或创建转录文本

        根据input_type决定是否需要转录:
        - audio: 调用TranscriptionService转录
        - text: 直接使用original_text

        Args:
            meeting: 会议记录对象

        Returns:
            转录文本

        Raises:
            TranscriptionError: 转录失败
            WorkflowError: 配置错误
        """
        if meeting.input_type == "audio":
            if not meeting.audio_key:
                raise WorkflowError("Audio meeting must have audio_key")

            logger.info(f"Starting transcription for audio: {meeting.audio_key}")

            # 启动转录作业
            job_id = await self.transcription.start_transcription(
                audio_s3_key=meeting.audio_key,
                language_code="zh-CN"
            )

            logger.info(f"Transcription job {job_id} started, waiting for completion...")

            # 等待转录完成(最长2小时)
            transcript = await self.transcription.wait_for_completion(
                job_id=job_id,
                max_wait_seconds=7200,
                poll_interval=5
            )

            logger.info(f"Transcription completed, length: {len(transcript)} chars")
            return transcript

        elif meeting.input_type == "text":
            if not meeting.original_text:
                raise WorkflowError("Text meeting must have original_text")
            return meeting.original_text

        else:
            raise WorkflowError(f"Unknown input_type: {meeting.input_type}")

    async def _load_template(self, template_id: str) -> Template:
        """
        加载模板

        Args:
            template_id: 模板ID

        Returns:
            Template对象

        Raises:
            WorkflowError: 模板不存在
        """
        template = await self.template_repo.get(template_id)
        if not template:
            # 尝试加载默认模板
            logger.warning(f"Template {template_id} not found, using default")
            template = await self.template_repo.get_default()

            if not template:
                raise WorkflowError("No template available")

        return template

    async def _call_ai_with_retry(self, ai_func, *args, **kwargs):
        """
        带重试的AI调用

        Args:
            ai_func: AI服务方法
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            AI调用结果

        Raises:
            WorkflowError: 重试次数用尽后仍失败
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                result = await ai_func(*args, **kwargs)

                if attempt > 0:
                    logger.info(f"AI call succeeded on attempt {attempt + 1}")

                return result

            except Exception as e:
                last_error = e

                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(
                        f"AI call failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                        f", retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"AI call failed after {self.max_retries} attempts: {e}"
                    )

        raise WorkflowError(f"AI调用失败(已重试{self.max_retries}次): {str(last_error)}") from last_error

    async def _handle_stage_failure(
        self,
        meeting_id: str,
        stage_name: str,
        error: Exception
    ) -> None:
        """
        处理阶段失败

        记录错误信息并更新meeting状态为failed

        Args:
            meeting_id: 会议记录ID
            stage_name: 阶段名称
            error: 异常对象
        """
        try:
            meeting = await self.meeting_repo.get(meeting_id)
            if not meeting:
                logger.error(f"Cannot update failed status: meeting {meeting_id} not found")
                return

            # 更新状态为失败
            meeting.status = "failed"
            meeting.updated_at = datetime.now(UTC)

            # 更新阶段状态并保存错误信息
            if stage_name in meeting.stages:
                stage = meeting.stages[stage_name]
                if isinstance(stage, ProcessingStage):
                    stage.status = "failed"
                    stage.completed_at = datetime.now(UTC)
                    # 将错误信息保存到metadata(如果metadata不存在则创建)
                    if not stage.metadata:
                        stage.metadata = ProcessingMetadata()
                    # 注: ProcessingMetadata没有error字段,我们通过model字段传递错误信息
                    # 或者可以扩展metadata
            else:
                # 如果阶段不存在,创建一个失败的阶段记录
                meeting.stages[stage_name] = ProcessingStage(
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                    status="failed",
                    metadata=ProcessingMetadata(
                        model=f"ERROR: {str(error)[:200]}"  # 截断错误信息
                    )
                )

            # 保存更新
            await self.meeting_repo.save(meeting)

            logger.info(f"Updated meeting {meeting_id} status to failed")

        except Exception as e:
            logger.error(f"Failed to update meeting status: {e}")

    async def get_stage_status(self, meeting_id: str, stage_name: str) -> Optional[str]:
        """
        获取指定阶段的状态

        Args:
            meeting_id: 会议记录ID
            stage_name: 阶段名称(draft/review/final)

        Returns:
            阶段状态字符串或None(如果阶段不存在)
        """
        meeting = await self.meeting_repo.get(meeting_id)
        if not meeting or stage_name not in meeting.stages:
            return None

        stage = meeting.stages[stage_name]
        if isinstance(stage, ProcessingStage):
            return stage.status
        elif isinstance(stage, ReviewStage):
            return "completed" if stage.completed_at else "processing"

        return None

    async def can_start_optimization(self, meeting_id: str) -> bool:
        """
        检查是否可以开始优化阶段

        条件:
        1. meeting存在
        2. draft阶段已完成
        3. 当前状态为reviewing

        Args:
            meeting_id: 会议记录ID

        Returns:
            是否可以开始优化
        """
        meeting = await self.meeting_repo.get(meeting_id)
        if not meeting:
            return False

        # 检查draft阶段
        if 'draft' not in meeting.stages:
            return False

        draft_stage = meeting.stages['draft']
        if not isinstance(draft_stage, ProcessingStage):
            return False

        if draft_stage.status != "completed":
            return False

        # 检查状态
        return meeting.status == "reviewing"
