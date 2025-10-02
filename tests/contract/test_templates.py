"""
Contract Tests for /api/v1/templates endpoints

这些测试验证API端点是否符合OpenAPI规范定义的契约。
按照TDD原则,这些测试应该先失败,然后通过实现代码使其通过。
"""

import pytest
from httpx import AsyncClient
from datetime import datetime
from uuid import UUID


BASE_URL = "http://localhost:8000"
TEMPLATES_ENDPOINT = f"{BASE_URL}/api/v1/templates"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_templates_success():
    """
    测试场景: GET /api/v1/templates - 成功获取所有模板

    契约验证:
    - HTTP状态码: 200
    - 响应Content-Type: application/json
    - 响应体: Template对象数组
    - 每个Template对象必须包含: id, name, is_default, structure, created_at
    """
    async with AsyncClient() as client:
        response = await client.get(TEMPLATES_ENDPOINT)

        # 验证状态码
        assert response.status_code == 200, (
            f"期望状态码200,实际得到{response.status_code}"
        )

        # 验证Content-Type
        assert response.headers["content-type"] == "application/json", (
            f"期望Content-Type为application/json,实际得到{response.headers.get('content-type')}"
        )

        # 验证响应体结构
        templates = response.json()
        assert isinstance(templates, list), "响应必须是数组"

        # 如果有模板,验证模板结构
        if len(templates) > 0:
            for template in templates:
                _validate_template_structure(template)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_templates_includes_default():
    """
    测试场景: GET /api/v1/templates - 确保响应中包含默认模板

    契约验证:
    - 至少有一个模板的is_default为true
    - 默认模板必须存在
    """
    async with AsyncClient() as client:
        response = await client.get(TEMPLATES_ENDPOINT)

        assert response.status_code == 200
        templates = response.json()

        # 验证至少存在一个默认模板
        default_templates = [t for t in templates if t.get("is_default") is True]
        assert len(default_templates) >= 1, (
            "必须至少包含一个默认模板(is_default=true)"
        )

        # 验证默认模板结构完整性
        default_template = default_templates[0]
        assert default_template["name"], "默认模板必须有名称"
        assert default_template["structure"], "默认模板必须有structure定义"
        assert "sections" in default_template["structure"], (
            "默认模板structure必须包含sections"
        )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_create_template_success():
    """
    测试场景: POST /api/v1/templates - 成功创建自定义模板

    契约验证:
    - HTTP状态码: 201
    - 响应Content-Type: application/json
    - 响应体: Template对象
    - 返回的Template包含所有必需字段
    - is_default为false(自定义模板)
    """
    # 构造符合TemplateInput schema的请求体
    template_input = {
        "name": "项目复盘会议模板",
        "structure": {
            "sections": [
                {
                    "name": "项目信息",
                    "fields": [
                        {"key": "project_name", "label": "项目名称", "required": True},
                        {"key": "sprint", "label": "Sprint编号", "required": True}
                    ]
                },
                {
                    "name": "复盘内容",
                    "fields": [
                        {"key": "what_went_well", "label": "做得好的地方", "required": True},
                        {"key": "what_to_improve", "label": "需要改进的地方", "required": True},
                        {"key": "action_items", "label": "行动项", "required": False}
                    ]
                }
            ]
        }
    }

    async with AsyncClient() as client:
        response = await client.post(
            TEMPLATES_ENDPOINT,
            json=template_input
        )

        # 验证状态码
        assert response.status_code == 201, (
            f"期望状态码201,实际得到{response.status_code}"
        )

        # 验证Content-Type
        assert response.headers["content-type"] == "application/json", (
            f"期望Content-Type为application/json"
        )

        # 验证响应体结构
        created_template = response.json()
        _validate_template_structure(created_template)

        # 验证输入数据被正确保存
        assert created_template["name"] == template_input["name"], (
            "返回的模板名称应与输入一致"
        )
        assert created_template["structure"] == template_input["structure"], (
            "返回的模板结构应与输入一致"
        )

        # 验证自定义模板不是默认模板
        assert created_template["is_default"] is False, (
            "自定义模板的is_default应为false"
        )

        # 验证生成了UUID格式的ID
        try:
            UUID(created_template["id"])
        except ValueError:
            pytest.fail(f"模板ID应为UUID格式,实际得到: {created_template['id']}")

        # 验证created_at是有效的ISO 8601日期时间
        try:
            datetime.fromisoformat(created_template["created_at"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail(f"created_at应为ISO 8601格式,实际得到: {created_template['created_at']}")


@pytest.mark.contract
@pytest.mark.asyncio
async def test_create_template_invalid_structure():
    """
    测试场景: POST /api/v1/templates - 模板结构无效,返回400错误

    契约验证:
    - HTTP状态码: 400
    - 响应Content-Type: application/json
    - 响应体: Error对象 (包含error和message字段)

    测试各种无效结构:
    1. structure缺少sections字段
    2. sections不是数组
    3. section缺少name或fields
    4. field缺少key或label
    """
    invalid_templates = [
        {
            "name": "无效模板1",
            "structure": {
                # 缺少sections字段
                "invalid_field": "test"
            }
        },
        {
            "name": "无效模板2",
            "structure": {
                "sections": "not_an_array"  # sections不是数组
            }
        },
        {
            "name": "无效模板3",
            "structure": {
                "sections": [
                    {
                        # 缺少name字段
                        "fields": []
                    }
                ]
            }
        },
        {
            "name": "无效模板4",
            "structure": {
                "sections": [
                    {
                        "name": "测试",
                        "fields": [
                            {
                                # 缺少key字段
                                "label": "测试字段"
                            }
                        ]
                    }
                ]
            }
        }
    ]

    async with AsyncClient() as client:
        for invalid_template in invalid_templates:
            response = await client.post(
                TEMPLATES_ENDPOINT,
                json=invalid_template
            )

            # 验证返回400错误
            assert response.status_code == 400, (
                f"无效结构应返回400,实际得到{response.status_code}。"
                f"输入: {invalid_template}"
            )

            # 验证错误响应结构
            error_response = response.json()
            assert "error" in error_response, "错误响应必须包含error字段"
            assert "message" in error_response, "错误响应必须包含message字段"
            assert isinstance(error_response["error"], str), "error字段必须是字符串"
            assert isinstance(error_response["message"], str), "message字段必须是字符串"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_create_template_missing_required_fields():
    """
    测试场景: POST /api/v1/templates - 缺少必需字段,返回400错误

    契约验证:
    - 缺少name字段
    - 缺少structure字段
    - 两个都缺少
    """
    invalid_inputs = [
        {
            # 缺少name
            "structure": {
                "sections": []
            }
        },
        {
            # 缺少structure
            "name": "测试模板"
        },
        {
            # 两个都缺少
        }
    ]

    async with AsyncClient() as client:
        for invalid_input in invalid_inputs:
            response = await client.post(
                TEMPLATES_ENDPOINT,
                json=invalid_input
            )

            assert response.status_code == 400, (
                f"缺少必需字段应返回400,实际得到{response.status_code}。"
                f"输入: {invalid_input}"
            )

            error_response = response.json()
            assert "error" in error_response
            assert "message" in error_response


@pytest.mark.contract
@pytest.mark.asyncio
async def test_create_template_name_too_long():
    """
    测试场景: POST /api/v1/templates - 模板名称超过100字符,返回400错误

    契约验证:
    - 按照schema定义,name的maxLength为100
    """
    template_input = {
        "name": "A" * 101,  # 101个字符,超过限制
        "structure": {
            "sections": [
                {
                    "name": "测试",
                    "fields": [
                        {"key": "test", "label": "测试"}
                    ]
                }
            ]
        }
    }

    async with AsyncClient() as client:
        response = await client.post(
            TEMPLATES_ENDPOINT,
            json=template_input
        )

        assert response.status_code == 400, (
            f"名称过长应返回400,实际得到{response.status_code}"
        )

        error_response = response.json()
        assert "error" in error_response
        assert "message" in error_response


# Helper functions

def _validate_template_structure(template: dict):
    """
    验证Template对象是否符合OpenAPI schema定义

    Template schema必需字段:
    - id: string (UUID格式)
    - name: string (最大100字符)
    - is_default: boolean
    - structure: object
    - created_at: string (ISO 8601日期时间)
    """
    required_fields = ["id", "name", "is_default", "structure", "created_at"]

    for field in required_fields:
        assert field in template, (
            f"Template对象缺少必需字段: {field}"
        )

    # 验证字段类型
    assert isinstance(template["id"], str), "id必须是字符串"
    assert isinstance(template["name"], str), "name必须是字符串"
    assert isinstance(template["is_default"], bool), "is_default必须是布尔值"
    assert isinstance(template["structure"], dict), "structure必须是对象"
    assert isinstance(template["created_at"], str), "created_at必须是字符串"

    # 验证name长度限制
    assert len(template["name"]) <= 100, (
        f"name长度不能超过100字符,实际长度: {len(template['name'])}"
    )

    # 验证UUID格式
    try:
        UUID(template["id"])
    except ValueError:
        pytest.fail(f"id必须是UUID格式,实际值: {template['id']}")

    # 验证日期时间格式
    try:
        datetime.fromisoformat(template["created_at"].replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"created_at必须是ISO 8601格式,实际值: {template['created_at']}")

    # 验证structure包含sections
    assert "sections" in template["structure"], (
        "structure必须包含sections字段"
    )
    assert isinstance(template["structure"]["sections"], list), (
        "sections必须是数组"
    )


def _validate_error_structure(error: dict):
    """
    验证Error对象是否符合OpenAPI schema定义

    Error schema必需字段:
    - error: string
    - message: string
    - details: object (可选)
    """
    assert "error" in error, "Error对象必须包含error字段"
    assert "message" in error, "Error对象必须包含message字段"

    assert isinstance(error["error"], str), "error字段必须是字符串"
    assert isinstance(error["message"], str), "message字段必须是字符串"

    if "details" in error:
        assert isinstance(error["details"], dict), "details字段必须是对象"
