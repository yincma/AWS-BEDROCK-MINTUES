"""
测试全局反馈功能

测试UserFeedback模型对location='global'的支持
"""

import pytest
from datetime import datetime, UTC
from src.models.meeting import UserFeedback
from pydantic import ValidationError


def test_global_feedback_validation_success():
    """测试全局反馈的location验证 - 成功场景"""
    feedback = UserFeedback(
        id="123e4567-e89b-12d3-a456-426614174001",
        created_at=datetime.now(UTC),
        feedback_type="improvement",
        location="global",
        comment="整体语气应该更正式一些"
    )

    assert feedback.location == "global"
    assert feedback.is_global_feedback() is True


def test_specific_feedback_validation_success():
    """测试具体位置反馈的location验证 - 成功场景"""
    feedback = UserFeedback(
        id="123e4567-e89b-12d3-a456-426614174001",
        created_at=datetime.now(UTC),
        feedback_type="inaccurate",
        location="section:会议内容,line:3",
        comment="这一行信息不准确"
    )

    assert feedback.location == "section:会议内容,line:3"
    assert feedback.is_global_feedback() is False


def test_invalid_location_format():
    """测试无效的location格式 - 应该抛出ValidationError"""
    with pytest.raises(ValidationError) as exc_info:
        UserFeedback(
            id="123e4567-e89b-12d3-a456-426614174001",
            created_at=datetime.now(UTC),
            feedback_type="improvement",
            location="invalid_format",
            comment="这是一个错误格式"
        )

    # 验证错误信息包含正确的提示
    assert "location格式必须为" in str(exc_info.value)


def test_location_missing_line():
    """测试缺少line的location格式 - 应该抛出ValidationError"""
    with pytest.raises(ValidationError) as exc_info:
        UserFeedback(
            id="123e4567-e89b-12d3-a456-426614174001",
            created_at=datetime.now(UTC),
            feedback_type="missing",
            location="section:会议内容",
            comment="缺少line部分"
        )

    assert "location格式必须为" in str(exc_info.value)


def test_multiple_feedback_types():
    """测试不同类型的全局反馈"""
    feedback_types = ["improvement", "inaccurate", "missing"]

    for feedback_type in feedback_types:
        feedback = UserFeedback(
            id="123e4567-e89b-12d3-a456-426614174001",
            created_at=datetime.now(UTC),
            feedback_type=feedback_type,
            location="global",
            comment=f"全局{feedback_type}测试"
        )

        assert feedback.is_global_feedback() is True
        assert feedback.feedback_type == feedback_type


def test_is_global_feedback_method():
    """测试is_global_feedback()方法的正确性"""
    # 全局反馈
    global_fb = UserFeedback(
        id="123e4567-e89b-12d3-a456-426614174001",
        created_at=datetime.now(UTC),
        feedback_type="improvement",
        location="global",
        comment="全局建议"
    )

    # 具体位置反馈
    specific_fb = UserFeedback(
        id="123e4567-e89b-12d3-a456-426614174002",
        created_at=datetime.now(UTC),
        feedback_type="inaccurate",
        location="section:决策事项,line:1",
        comment="具体位置反馈"
    )

    assert global_fb.is_global_feedback() is True
    assert specific_fb.is_global_feedback() is False
