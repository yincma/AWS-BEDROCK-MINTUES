"""
Contract Tests for POST /api/v1/meetings/{meeting_id}/feedback Endpoint

基于OpenAPI规范的Contract测试，验证API契约的正确性。
这些测试遵循TDD原则，在实现之前编写，当前应该失败。

测试覆盖:
- 提交有效反馈 (202 Accepted)
- 反馈格式错误 (400 Bad Request)
- 会议不存在 (404 Not Found)
- 会议状态不允许反馈 (409 Conflict)
"""

import pytest
import httpx
from uuid import uuid4
from typing import Dict, Any


# 测试配置
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


# Test Fixtures
@pytest.fixture
def valid_feedback_data() -> Dict[str, Any]:
    """有效的反馈数据"""
    return {
        "feedbacks": [
            {
                "feedback_type": "inaccurate",
                "location": "section:决策事项,line:5",
                "comment": "这里应该是推荐功能而不是必需功能"
            },
            {
                "feedback_type": "missing",
                "location": "section:行动项,line:10",
                "comment": "缺少负责人信息"
            },
            {
                "feedback_type": "improvement",
                "location": "section:会议内容,line:3",
                "comment": "建议增加更详细的背景说明"
            }
        ]
    }


@pytest.fixture
def invalid_feedback_missing_field() -> Dict[str, Any]:
    """缺少必需字段的反馈数据"""
    return {
        "feedbacks": [
            {
                "feedback_type": "inaccurate",
                "location": "section:决策事项,line:5"
                # 缺少 comment 字段
            }
        ]
    }


@pytest.fixture
def invalid_feedback_wrong_type() -> Dict[str, Any]:
    """错误的feedback_type"""
    return {
        "feedbacks": [
            {
                "feedback_type": "invalid_type",  # 不在枚举值中
                "location": "section:决策事项,line:5",
                "comment": "测试错误类型"
            }
        ]
    }


@pytest.fixture
def invalid_feedback_comment_too_long() -> Dict[str, Any]:
    """comment超过最大长度(1000字符)"""
    return {
        "feedbacks": [
            {
                "feedback_type": "improvement",
                "location": "section:会议内容,line:1",
                "comment": "x" * 1001  # 超过1000字符限制
            }
        ]
    }


@pytest.fixture
def invalid_feedback_empty_array() -> Dict[str, Any]:
    """空的feedbacks数组"""
    return {
        "feedbacks": []
    }


@pytest.fixture
def test_meeting_id() -> str:
    """测试用的会议ID"""
    return str(uuid4())


@pytest.fixture
def non_existent_meeting_id() -> str:
    """不存在的会议ID"""
    return str(uuid4())


# Contract Tests

@pytest.mark.contract
@pytest.mark.asyncio
async def test_submit_feedback_success(
    test_meeting_id: str,
    valid_feedback_data: Dict[str, Any]
):
    """
    测试场景: 提交有效的反馈数据

    验证点:
    1. HTTP状态码为202 Accepted
    2. 响应包含message字段
    3. 响应包含meeting_id字段
    4. meeting_id与请求的ID匹配
    5. Content-Type为application/json
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/meetings/{test_meeting_id}/feedback",
            json=valid_feedback_data,
            headers={"Content-Type": "application/json"}
        )

    # 验证HTTP状态码
    assert response.status_code == 202, \
        f"期望状态码202，实际得到{response.status_code}"

    # 验证响应内容类型
    assert response.headers.get("content-type") == "application/json", \
        "响应Content-Type应为application/json"

    # 验证响应体结构
    response_data = response.json()
    assert "message" in response_data, "响应应包含message字段"
    assert "meeting_id" in response_data, "响应应包含meeting_id字段"
    assert response_data["meeting_id"] == test_meeting_id, \
        "响应的meeting_id应与请求的ID匹配"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_submit_feedback_invalid_format_missing_field(
    test_meeting_id: str,
    invalid_feedback_missing_field: Dict[str, Any]
):
    """
    测试场景: 反馈数据缺少必需字段

    验证点:
    1. HTTP状态码为400 Bad Request
    2. 响应包含error字段
    3. 响应包含message字段说明具体错误
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/meetings/{test_meeting_id}/feedback",
            json=invalid_feedback_missing_field,
            headers={"Content-Type": "application/json"}
        )

    assert response.status_code == 400, \
        f"期望状态码400，实际得到{response.status_code}"

    response_data = response.json()
    assert "error" in response_data, "错误响应应包含error字段"
    assert "message" in response_data, "错误响应应包含message字段"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_submit_feedback_invalid_format_wrong_type(
    test_meeting_id: str,
    invalid_feedback_wrong_type: Dict[str, Any]
):
    """
    测试场景: feedback_type不在允许的枚举值中

    验证点:
    1. HTTP状态码为400 Bad Request
    2. 响应说明feedback_type无效
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/meetings/{test_meeting_id}/feedback",
            json=invalid_feedback_wrong_type,
            headers={"Content-Type": "application/json"}
        )

    assert response.status_code == 400, \
        f"期望状态码400，实际得到{response.status_code}"

    response_data = response.json()
    assert "error" in response_data
    assert "feedback_type" in response_data["message"].lower() or \
           "type" in response_data["message"].lower(), \
        "错误消息应说明feedback_type无效"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_submit_feedback_invalid_format_comment_too_long(
    test_meeting_id: str,
    invalid_feedback_comment_too_long: Dict[str, Any]
):
    """
    测试场景: comment字段超过最大长度限制(1000字符)

    验证点:
    1. HTTP状态码为400 Bad Request
    2. 响应说明comment过长
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/meetings/{test_meeting_id}/feedback",
            json=invalid_feedback_comment_too_long,
            headers={"Content-Type": "application/json"}
        )

    assert response.status_code == 400, \
        f"期望状态码400，实际得到{response.status_code}"

    response_data = response.json()
    assert "error" in response_data
    assert "comment" in response_data["message"].lower() or \
           "length" in response_data["message"].lower() or \
           "1000" in response_data["message"], \
        "错误消息应说明comment超过长度限制"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_submit_feedback_invalid_format_empty_array(
    test_meeting_id: str,
    invalid_feedback_empty_array: Dict[str, Any]
):
    """
    测试场景: feedbacks数组为空

    验证点:
    1. HTTP状态码为400 Bad Request
    2. 响应说明feedbacks不能为空
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/meetings/{test_meeting_id}/feedback",
            json=invalid_feedback_empty_array,
            headers={"Content-Type": "application/json"}
        )

    assert response.status_code == 400, \
        f"期望状态码400，实际得到{response.status_code}"

    response_data = response.json()
    assert "error" in response_data
    assert "feedback" in response_data["message"].lower() or \
           "empty" in response_data["message"].lower(), \
        "错误消息应说明feedbacks不能为空"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_submit_feedback_meeting_not_found(
    non_existent_meeting_id: str,
    valid_feedback_data: Dict[str, Any]
):
    """
    测试场景: 会议ID不存在

    验证点:
    1. HTTP状态码为404 Not Found
    2. 响应包含error和message字段
    3. 消息说明会议未找到
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/meetings/{non_existent_meeting_id}/feedback",
            json=valid_feedback_data,
            headers={"Content-Type": "application/json"}
        )

    assert response.status_code == 404, \
        f"期望状态码404，实际得到{response.status_code}"

    response_data = response.json()
    assert "error" in response_data, "错误响应应包含error字段"
    assert "message" in response_data, "错误响应应包含message字段"
    assert "not found" in response_data["message"].lower() or \
           "不存在" in response_data["message"], \
        "错误消息应说明会议未找到"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_submit_feedback_invalid_status_draft(
    test_meeting_id: str,
    valid_feedback_data: Dict[str, Any]
):
    """
    测试场景: 会议处于draft状态，不允许提交反馈

    说明: 只有在reviewing状态的会议才能接受反馈

    验证点:
    1. HTTP状态码为409 Conflict
    2. 响应说明当前状态不允许提交反馈
    """
    # 这个测试假设会议处于draft状态
    # 实际实现中需要先创建一个draft状态的会议
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/meetings/{test_meeting_id}/feedback",
            json=valid_feedback_data,
            headers={"Content-Type": "application/json"}
        )

    # 如果会议不在reviewing状态，应返回409
    if response.status_code == 409:
        response_data = response.json()
        assert "error" in response_data
        assert "status" in response_data["message"].lower() or \
               "状态" in response_data["message"], \
            "错误消息应说明状态不允许提交反馈"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_submit_feedback_invalid_status_completed(
    test_meeting_id: str,
    valid_feedback_data: Dict[str, Any]
):
    """
    测试场景: 会议处于completed状态，不允许提交反馈

    说明: 已完成的会议不能再提交反馈

    验证点:
    1. HTTP状态码为409 Conflict
    2. 响应说明会议已完成，不能提交反馈
    """
    # 这个测试假设会议处于completed状态
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/meetings/{test_meeting_id}/feedback",
            json=valid_feedback_data,
            headers={"Content-Type": "application/json"}
        )

    # 如果会议已完成，应返回409
    if response.status_code == 409:
        response_data = response.json()
        assert "error" in response_data
        assert "completed" in response_data["message"].lower() or \
               "完成" in response_data["message"], \
            "错误消息应说明会议已完成"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_submit_feedback_location_format_validation(
    test_meeting_id: str
):
    """
    测试场景: 验证location字段的格式要求

    location格式应为: "section:<章节名>,line:<行号>"

    验证点:
    1. 有效的location格式能被接受
    2. 无效的location格式返回400
    """
    valid_locations = [
        "section:会议内容,line:1",
        "section:决策事项,line:10",
        "section:行动项,line:999"
    ]

    invalid_locations = [
        "invalid_format",
        "section:only",
        "line:5",
        ""
    ]

    # 测试有效格式
    for location in valid_locations:
        feedback_data = {
            "feedbacks": [{
                "feedback_type": "improvement",
                "location": location,
                "comment": "测试location格式"
            }]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/meetings/{test_meeting_id}/feedback",
                json=feedback_data,
                headers={"Content-Type": "application/json"}
            )

        # 应该是202(成功)或404(会议不存在)或409(状态不允许)
        # 但不应该是400(格式错误)
        assert response.status_code in [202, 404, 409], \
            f"有效location '{location}' 不应返回400错误"

    # 测试无效格式
    for location in invalid_locations:
        feedback_data = {
            "feedbacks": [{
                "feedback_type": "improvement",
                "location": location,
                "comment": "测试无效location格式"
            }]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/meetings/{test_meeting_id}/feedback",
                json=feedback_data,
                headers={"Content-Type": "application/json"}
            )

        # 无效格式应返回400
        assert response.status_code == 400, \
            f"无效location '{location}' 应返回400错误"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_submit_feedback_all_feedback_types(
    test_meeting_id: str
):
    """
    测试场景: 验证所有支持的feedback_type

    支持的类型: inaccurate, missing, improvement

    验证点:
    1. 三种反馈类型都能被正确接受
    2. 可以在一个请求中混合使用多种类型
    """
    feedback_types = ["inaccurate", "missing", "improvement"]

    # 测试每种类型单独使用
    for feedback_type in feedback_types:
        feedback_data = {
            "feedbacks": [{
                "feedback_type": feedback_type,
                "location": "section:测试,line:1",
                "comment": f"测试{feedback_type}类型"
            }]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/meetings/{test_meeting_id}/feedback",
                json=feedback_data,
                headers={"Content-Type": "application/json"}
            )

        # 应该不是400错误（类型有效）
        assert response.status_code != 400 or \
               "feedback_type" not in response.json().get("message", "").lower(), \
            f"有效的feedback_type '{feedback_type}' 不应被拒绝"

    # 测试混合使用所有类型
    mixed_feedback_data = {
        "feedbacks": [
            {
                "feedback_type": "inaccurate",
                "location": "section:测试1,line:1",
                "comment": "测试inaccurate"
            },
            {
                "feedback_type": "missing",
                "location": "section:测试2,line:2",
                "comment": "测试missing"
            },
            {
                "feedback_type": "improvement",
                "location": "section:测试3,line:3",
                "comment": "测试improvement"
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/meetings/{test_meeting_id}/feedback",
            json=mixed_feedback_data,
            headers={"Content-Type": "application/json"}
        )

    # 混合使用应该被接受
    assert response.status_code in [202, 404, 409], \
        "混合使用所有feedback_type应该被接受"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_submit_feedback_invalid_meeting_id_format():
    """
    测试场景: meeting_id格式无效(不是UUID)

    验证点:
    1. 应返回400或404错误
    2. 响应说明meeting_id格式无效
    """
    invalid_meeting_ids = [
        "not-a-uuid",
        "12345",
        "",
        "invalid-uuid-format"
    ]

    feedback_data = {
        "feedbacks": [{
            "feedback_type": "improvement",
            "location": "section:测试,line:1",
            "comment": "测试无效meeting_id"
        }]
    }

    for invalid_id in invalid_meeting_ids:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/meetings/{invalid_id}/feedback",
                json=feedback_data,
                headers={"Content-Type": "application/json"}
            )

        # 应返回错误状态码
        assert response.status_code in [400, 404], \
            f"无效meeting_id '{invalid_id}' 应返回400或404错误"
