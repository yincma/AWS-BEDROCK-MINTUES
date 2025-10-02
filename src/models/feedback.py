"""用户反馈相关的Pydantic模型

包含:
- FeedbackInput: API请求模型
- FeedbackBatch: 批量反馈模型
- create_feedback_from_input: 辅助函数

注意：UserFeedback 类定义在 models/meeting.py 中（单一数据源原则）
"""

from datetime import datetime, UTC
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator
from .meeting import UserFeedback


# 类型别名，方便理解
FeedbackType = Literal["inaccurate", "missing", "improvement"]


class FeedbackInput(BaseModel):
    """用户提交反馈的请求模型

    用于API端点接收用户反馈数据。
    """

    feedback_type: FeedbackType = Field(description="反馈类型")
    location: str = Field(description="格式: 'global'(全局优化建议) 或 'section:<章节名>,line:<行号>'(具体位置反馈)")
    comment: str = Field(max_length=1000, description="反馈内容")

    @field_validator("location")
    @classmethod
    def validate_location_format(cls, v: str) -> str:
        """验证location格式正确

        格式要求:
        - 'global': 全局优化建议，无需指定具体位置
        - 'section:<章节名>,line:<行号>': 具体位置反馈

        Args:
            v: location字符串

        Returns:
            验证通过的location字符串

        Raises:
            ValueError: 格式不正确时
        """
        # 支持全局反馈
        if v == "global":
            return v

        # 验证具体位置格式
        if "," not in v or not v.startswith("section:"):
            raise ValueError("location格式必须为 'global' 或 'section:<名称>,line:<行号>'")

        parts = v.split(",")
        if len(parts) != 2:
            raise ValueError("location必须包含section和line两部分")

        if not parts[0].startswith("section:"):
            raise ValueError("第一部分必须是section:")

        if not parts[1].strip().startswith("line:"):
            raise ValueError("第二部分必须是line:")

        return v


class FeedbackBatch(BaseModel):
    """批量提交反馈的请求体

    允许用户一次提交多个反馈。
    """

    feedbacks: list[FeedbackInput] = Field(min_length=1, description="至少包含一个反馈")


def create_feedback_from_input(
    feedback_input: FeedbackInput, feedback_id: str | None = None
) -> UserFeedback:
    """从FeedbackInput创建UserFeedback

    将API请求模型转换为完整的存储模型，自动生成ID和时间戳。

    Args:
        feedback_input: API请求数据
        feedback_id: 可选的自定义ID，默认生成UUID

    Returns:
        完整的UserFeedback对象（定义在 models/meeting.py）

    Example:
        >>> input_data = FeedbackInput(
        ...     feedback_type="inaccurate",
        ...     location="section:介绍,line:5",
        ...     comment="此处描述不准确"
        ... )
        >>> feedback = create_feedback_from_input(input_data)
        >>> feedback.is_resolved
        False
    """
    return UserFeedback(
        id=feedback_id or str(uuid4()),
        created_at=datetime.now(UTC),
        feedback_type=feedback_input.feedback_type,
        location=feedback_input.location,
        comment=feedback_input.comment,
        is_resolved=False,
    )
