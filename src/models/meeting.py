"""
会议记录相关的Pydantic模型定义

基于data-model.md中的JSON Schema定义,用于验证和序列化会议记录数据到S3
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class TokensUsed(BaseModel):
    """LLM令牌使用情况"""

    input: int = Field(ge=0, description="输入令牌数")
    output: int = Field(ge=0, description="输出令牌数")

    model_config = {"json_schema_extra": {"example": {"input": 10000, "output": 3000}}}


class ProcessingMetadata(BaseModel):
    """处理阶段元数据"""

    processing_time_seconds: Optional[float] = Field(None, ge=0, description="处理耗时(秒)")
    tokens_used: Optional[TokensUsed] = None
    model: Optional[str] = Field(None, description="使用的AI模型")

    model_config = {
        "json_schema_extra": {
            "example": {
                "processing_time_seconds": 45.0,
                "tokens_used": {"input": 10000, "output": 3000},
                "model": "amazon.nova-pro-v1:0",
            }
        }
    }


class ProcessingStage(BaseModel):
    """处理阶段(draft/final)"""

    started_at: datetime = Field(description="阶段开始时间")
    completed_at: Optional[datetime] = Field(None, description="阶段完成时间")
    status: Literal["pending", "processing", "completed", "failed"] = Field(
        default="pending", description="阶段状态"
    )
    content: Optional[str] = Field(None, description="Markdown格式的会议记录内容")
    metadata: ProcessingMetadata = Field(
        default_factory=ProcessingMetadata, description="处理元数据"
    )

    @field_validator("completed_at")
    @classmethod
    def validate_completed_at(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """验证完成时间必须晚于开始时间"""
        if v is not None:
            started_at = info.data.get("started_at")
            if started_at and v < started_at:
                raise ValueError("completed_at必须晚于started_at")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "started_at": "2025-10-01T10:10:00Z",
                "completed_at": "2025-10-01T10:20:00Z",
                "status": "completed",
                "content": "# 会议记录\n\n## 会议基本信息...",
                "metadata": {
                    "processing_time_seconds": 45,
                    "tokens_used": {"input": 10000, "output": 3000},
                    "model": "amazon.nova-pro-v1:0",
                },
            }
        }
    }


class UserFeedback(BaseModel):
    """用户反馈(内嵌在ReviewStage中)"""

    id: str = Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        description="反馈唯一标识(UUID)",
    )
    created_at: datetime = Field(description="创建时间")
    feedback_type: Literal["inaccurate", "missing", "improvement"] = Field(
        description="反馈类型"
    )
    location: str = Field(
        description="反馈位置,格式: 'global'(全局优化建议) 或 'section:<名称>,line:<行号>'(具体位置反馈)"
    )
    comment: str = Field(max_length=1000, description="反馈内容")
    is_resolved: bool = Field(default=False, description="是否已解决")

    @field_validator("location")
    @classmethod
    def validate_location_format(cls, v: str) -> str:
        """验证location格式: 支持'global'或'section:<名称>,line:<行号>'"""
        if v == "global":
            return v
        if not v.startswith("section:") or ",line:" not in v:
            raise ValueError("location格式必须为: 'global' 或 'section:<名称>,line:<行号>'")
        return v

    def is_global_feedback(self) -> bool:
        """判断是否为全局优化建议"""
        return self.location == "global"

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "created_at": "2025-10-01T10:25:00Z",
                "feedback_type": "inaccurate",
                "location": "section:决策事项,line:1",
                "comment": "应该是推荐功能而不是AI功能",
                "is_resolved": True,
            }
        }
    }


class ReviewStage(BaseModel):
    """审核阶段"""

    started_at: datetime = Field(description="审核开始时间")
    completed_at: Optional[datetime] = Field(None, description="审核完成时间")
    feedbacks: List[UserFeedback] = Field(default_factory=list, description="用户反馈列表")

    @field_validator("completed_at")
    @classmethod
    def validate_completed_at(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """验证完成时间必须晚于开始时间"""
        if v is not None:
            started_at = info.data.get("started_at")
            if started_at and v < started_at:
                raise ValueError("completed_at必须晚于started_at")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "started_at": "2025-10-01T10:20:00Z",
                "completed_at": "2025-10-01T10:30:00Z",
                "feedbacks": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174001",
                        "created_at": "2025-10-01T10:25:00Z",
                        "feedback_type": "inaccurate",
                        "location": "section:决策事项,line:1",
                        "comment": "应该是推荐功能而不是AI功能",
                        "is_resolved": True,
                    }
                ],
            }
        }
    }


class MeetingMinute(BaseModel):
    """
    会议记录主模型

    存储在S3: meetings/{meeting_id}.json
    """

    id: str = Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        description="会议记录唯一标识(UUID v4)",
    )
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后更新时间")
    status: Literal["draft", "reviewing", "optimized", "completed", "failed"] = Field(
        description="当前处理状态"
    )
    input_type: Literal["audio", "text"] = Field(description="输入类型")
    audio_key: Optional[str] = Field(None, description="S3音频文件key(如果input_type=audio)")
    audio_duration_seconds: Optional[int] = Field(
        None, ge=0, le=7200, description="音频时长(秒),最大2小时"
    )
    original_text: Optional[str] = Field(None, description="原始文本(转录结果或用户输入)")
    template_id: str = Field(description="使用的模板ID")
    current_stage: Literal["draft", "review", "final"] = Field(description="当前所处阶段")
    stages: Dict[str, Union[ProcessingStage, ReviewStage]] = Field(
        default_factory=dict, description="各阶段数据(draft/review/final)"
    )

    @field_validator("audio_key")
    @classmethod
    def validate_audio_key_format(cls, v: Optional[str]) -> Optional[str]:
        """验证audio_key格式"""
        if v is not None and not v.startswith("audio/"):
            raise ValueError("audio_key必须以'audio/'开头")
        return v

    @model_validator(mode="after")
    def validate_audio_fields(self) -> "MeetingMinute":
        """验证audio相关字段的一致性"""
        if self.input_type == "audio":
            if not self.audio_key:
                raise ValueError("input_type为audio时必须提供audio_key")
            if self.audio_duration_seconds is None:
                raise ValueError("input_type为audio时必须提供audio_duration_seconds")
        return self

    @model_validator(mode="after")
    def validate_updated_at(self) -> "MeetingMinute":
        """验证updated_at必须晚于或等于created_at"""
        if self.updated_at < self.created_at:
            raise ValueError("updated_at必须晚于或等于created_at")
        return self

    @model_validator(mode="after")
    def validate_stages_consistency(self) -> "MeetingMinute":
        """验证stages与current_stage的一致性"""
        # 验证current_stage在stages中存在
        if self.stages and self.current_stage not in self.stages:
            raise ValueError(f"current_stage '{self.current_stage}' 不存在于stages中")

        # 验证stages的类型正确性
        for stage_name, stage_data in self.stages.items():
            if stage_name == "review":
                if not isinstance(stage_data, ReviewStage):
                    raise ValueError(f"stage '{stage_name}' 必须是ReviewStage类型")
            elif stage_name in ("draft", "final"):
                if not isinstance(stage_data, ProcessingStage):
                    raise ValueError(f"stage '{stage_name}' 必须是ProcessingStage类型")
            else:
                raise ValueError(f"无效的stage名称: {stage_name}, 必须是draft/review/final之一")

        return self

    def to_s3_json(self) -> str:
        """
        序列化为S3 JSON格式

        Returns:
            格式化的JSON字符串(不转义中文,缩进2空格)
        """
        # 使用model_dump获取字典,然后手动序列化以确保格式正确
        data = self.model_dump(mode="json")
        return json.dumps(data, ensure_ascii=False, indent=2)

    @classmethod
    def from_s3_json(cls, json_str: str) -> "MeetingMinute":
        """
        从S3 JSON字符串反序列化

        Args:
            json_str: JSON字符串

        Returns:
            MeetingMinute实例
        """
        return cls.model_validate_json(json_str)

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "created_at": "2025-10-01T10:00:00Z",
                "updated_at": "2025-10-01T10:35:00Z",
                "status": "completed",
                "input_type": "audio",
                "audio_key": "audio/123e4567-e89b-12d3-a456-426614174000.mp3",
                "audio_duration_seconds": 3600,
                "original_text": "会议转录文本...",
                "template_id": "default",
                "current_stage": "final",
                "stages": {
                    "draft": {
                        "started_at": "2025-10-01T10:10:00Z",
                        "completed_at": "2025-10-01T10:20:00Z",
                        "status": "completed",
                        "content": "# 会议记录\n\n## 会议基本信息...",
                        "metadata": {
                            "processing_time_seconds": 45,
                            "tokens_used": {"input": 10000, "output": 3000},
                            "model": "amazon.nova-pro-v1:0",
                        },
                    },
                    "review": {
                        "started_at": "2025-10-01T10:20:00Z",
                        "completed_at": "2025-10-01T10:30:00Z",
                        "feedbacks": [
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174001",
                                "created_at": "2025-10-01T10:25:00Z",
                                "feedback_type": "inaccurate",
                                "location": "section:决策事项,line:1",
                                "comment": "应该是推荐功能而不是AI功能",
                                "is_resolved": True,
                            }
                        ],
                    },
                    "final": {
                        "started_at": "2025-10-01T10:30:00Z",
                        "completed_at": "2025-10-01T10:35:00Z",
                        "status": "completed",
                        "content": "# 会议记录 (优化版)\n\n## 会议基本信息...",
                        "metadata": {
                            "processing_time_seconds": 15,
                            "tokens_used": {"input": 12000, "output": 3200},
                            "model": "amazon.nova-pro-v1:0",
                        },
                    },
                },
            }
        }
    }
