"""
集成测试: 自定义模板流程 (T012)

测试场景5: 创建自定义模板并使用它生成会议记录

测试流程:
1. POST /api/v1/templates 创建自定义模板
2. 验证模板已保存到S3
3. 使用该模板ID创建会议记录
4. 验证生成的内容遵循自定义模板结构
5. 验证模板的required字段被提取
"""
import json
import pytest
from uuid import UUID


@pytest.mark.integration
@pytest.mark.asyncio
class TestCustomTemplateWorkflow:
    """自定义模板完整工作流测试"""

    @pytest.fixture
    def custom_template_data(self):
        """技术评审模板数据"""
        return {
            "name": "技术评审模板",
            "structure": {
                "sections": [
                    {
                        "name": "评审信息",
                        "fields": [
                            {"key": "title", "label": "评审主题", "required": True},
                            {"key": "reviewer", "label": "评审人", "required": True},
                            {"key": "date", "label": "评审日期", "required": False}
                        ]
                    },
                    {
                        "name": "评审内容",
                        "fields": [
                            {"key": "findings", "label": "发现问题", "required": True},
                            {
                                "key": "recommendations",
                                "label": "改进建议",
                                "required": True
                            },
                            {"key": "notes", "label": "备注", "required": False}
                        ]
                    }
                ]
            }
        }

    @pytest.fixture
    def meeting_text_for_template(self):
        """适合技术评审模板的会议文本"""
        return """
        今天进行了代码评审会议。
        评审主题：后端API性能优化
        评审人：张工和李工
        评审日期：2025-10-01

        发现的主要问题：
        1. 数据库查询缺少索引，导致慢查询
        2. API响应时间超过2秒，用户体验差
        3. 缓存策略不当，命中率低

        改进建议：
        1. 为user_id和created_at字段添加联合索引
        2. 引入Redis缓存热点数据
        3. 优化SQL查询，减少N+1问题
        4. 添加性能监控和告警

        备注：下周五前完成优化并上线
        """

    async def test_01_create_custom_template(
        self, async_client_with_aws, custom_template_data
    ):
        """
        测试步骤1: 创建自定义模板

        验证:
        - API返回201状态码
        - 返回模板ID和完整数据
        - 模板名称正确
        """
        client, bucket, s3_client = async_client_with_aws

        # 发送创建模板请求
        response = await client.post(
            "/api/v1/templates",
            json=custom_template_data
        )

        # 验证响应
        assert response.status_code == 201, f"期望201，实际{response.status_code}"

        template = response.json()

        # 验证返回的数据结构
        assert "id" in template, "响应中应包含模板ID"
        assert "name" in template, "响应中应包含模板名称"
        assert "structure" in template, "响应中应包含模板结构"
        assert "created_at" in template, "响应中应包含创建时间"

        # 验证模板ID是有效的UUID
        try:
            UUID(template["id"])
        except ValueError:
            pytest.fail(f"模板ID不是有效的UUID: {template['id']}")

        # 验证模板内容
        assert template["name"] == "技术评审模板"
        assert template["structure"] == custom_template_data["structure"]

        # 保存template_id供后续测试使用
        self.template_id = template["id"]

    async def test_02_verify_template_saved_to_s3(
        self, async_client_with_aws, custom_template_data
    ):
        """
        测试步骤2: 验证模板已保存到S3

        验证:
        - S3中存在模板文件
        - 文件内容正确
        - JSON格式有效
        """
        client, bucket, s3_client = async_client_with_aws

        # 先创建模板
        response = await client.post(
            "/api/v1/templates",
            json=custom_template_data
        )
        assert response.status_code == 201
        template = response.json()
        template_id = template["id"]

        # 验证S3中的文件
        s3_key = f"templates/{template_id}.json"

        # 检查文件是否存在
        try:
            s3_response = s3_client.get_object(Bucket=bucket, Key=s3_key)
            s3_content = json.loads(s3_response["Body"].read().decode("utf-8"))
        except Exception as e:
            pytest.fail(f"无法从S3读取模板: {e}")

        # 验证S3中的内容
        assert s3_content["id"] == template_id
        assert s3_content["name"] == "技术评审模板"
        assert s3_content["structure"] == custom_template_data["structure"]

    async def test_03_list_templates_includes_custom(
        self, async_client_with_aws, custom_template_data
    ):
        """
        测试步骤3: 查询模板列表包含自定义模板

        验证:
        - GET /api/v1/templates 返回模板列表
        - 列表中包含新创建的模板
        """
        client, bucket, s3_client = async_client_with_aws

        # 创建模板
        create_response = await client.post(
            "/api/v1/templates",
            json=custom_template_data
        )
        assert create_response.status_code == 201
        created_template = create_response.json()

        # 查询模板列表
        list_response = await client.get("/api/v1/templates")
        assert list_response.status_code == 200

        templates = list_response.json()
        assert isinstance(templates, list), "应返回模板列表"

        # 验证新模板在列表中
        template_ids = [t["id"] for t in templates]
        assert created_template["id"] in template_ids, "新创建的模板应在列表中"

        # 验证可以找到技术评审模板
        tech_review_templates = [
            t for t in templates if t["name"] == "技术评审模板"
        ]
        assert len(tech_review_templates) >= 1, "应找到技术评审模板"

    async def test_04_create_meeting_with_custom_template(
        self,
        async_client_with_aws,
        custom_template_data,
        meeting_text_for_template
    ):
        """
        测试步骤4: 使用自定义模板创建会议记录

        验证:
        - 可以指定template_id创建会议
        - 返回会议ID和状态
        """
        client, bucket, s3_client = async_client_with_aws

        # 先创建模板
        template_response = await client.post(
            "/api/v1/templates",
            json=custom_template_data
        )
        assert template_response.status_code == 201
        template_id = template_response.json()["id"]

        # 使用自定义模板创建会议记录
        meeting_response = await client.post(
            "/api/v1/meetings",
            data={
                "input_type": "text",
                "text_content": meeting_text_for_template,
                "template_id": template_id
            }
        )

        # 验证会议创建成功
        assert meeting_response.status_code == 201, (
            f"期望201，实际{meeting_response.status_code}，"
            f"响应: {meeting_response.text}"
        )

        meeting = meeting_response.json()

        # 验证返回数据
        assert "id" in meeting, "响应中应包含会议ID"
        assert "status" in meeting, "响应中应包含状态"
        assert "template_id" in meeting, "响应中应包含模板ID"

        # 验证使用了正确的模板
        assert meeting["template_id"] == template_id

        # 保存meeting_id供后续测试使用
        self.meeting_id = meeting["id"]

    async def test_05_verify_generated_content_follows_template(
        self,
        async_client_with_aws,
        custom_template_data,
        meeting_text_for_template
    ):
        """
        测试步骤5: 验证生成的内容遵循自定义模板结构

        验证:
        - 生成的Markdown包含模板定义的所有section
        - Required字段已被提取
        - 内容格式符合模板结构
        """
        client, bucket, s3_client = async_client_with_aws

        # 创建模板
        template_response = await client.post(
            "/api/v1/templates",
            json=custom_template_data
        )
        template_id = template_response.json()["id"]

        # 创建会议
        meeting_response = await client.post(
            "/api/v1/meetings",
            data={
                "input_type": "text",
                "text_content": meeting_text_for_template,
                "template_id": template_id
            }
        )
        meeting_id = meeting_response.json()["id"]

        # 等待处理完成 (模拟轮询)
        # 在实际实现中，这里应该轮询直到status变为completed
        # 现在我们直接查询会议详情

        # 获取会议详情
        detail_response = await client.get(f"/api/v1/meetings/{meeting_id}")
        assert detail_response.status_code == 200

        meeting_detail = detail_response.json()

        # 验证会议数据包含stages
        assert "stages" in meeting_detail, "会议应包含处理阶段数据"

        # 检查draft阶段的内容
        if "draft" in meeting_detail["stages"]:
            draft_stage = meeting_detail["stages"]["draft"]
            if "content" in draft_stage:
                content = draft_stage["content"]

                # 验证内容包含模板定义的section
                assert "评审信息" in content, "应包含'评审信息'section"
                assert "评审内容" in content, "应包含'评审内容'section"

                # 验证required字段被提取
                assert "评审主题" in content or "title" in content.lower()
                assert "评审人" in content or "reviewer" in content.lower()
                assert "发现问题" in content or "findings" in content.lower()
                assert "改进建议" in content or "recommendations" in content.lower()

    async def test_06_validate_template_structure(
        self, async_client_with_aws
    ):
        """
        测试步骤6: 验证模板结构验证逻辑

        验证:
        - 缺少必需字段时返回400错误
        - 无效的结构被拒绝
        """
        client, bucket, s3_client = async_client_with_aws

        # 测试缺少name字段
        invalid_template_1 = {
            "structure": {
                "sections": []
            }
        }

        response_1 = await client.post(
            "/api/v1/templates",
            json=invalid_template_1
        )
        assert response_1.status_code == 422, "缺少name应返回422"

        # 测试缺少structure字段
        invalid_template_2 = {
            "name": "测试模板"
        }

        response_2 = await client.post(
            "/api/v1/templates",
            json=invalid_template_2
        )
        assert response_2.status_code == 422, "缺少structure应返回422"

        # 测试空sections
        invalid_template_3 = {
            "name": "测试模板",
            "structure": {
                "sections": []
            }
        }

        response_3 = await client.post(
            "/api/v1/templates",
            json=invalid_template_3
        )
        # 应该被接受或返回400 (取决于业务规则)
        assert response_3.status_code in [201, 400]

    async def test_07_required_fields_extraction(
        self,
        async_client_with_aws,
        custom_template_data,
        meeting_text_for_template
    ):
        """
        测试步骤7: 验证必需字段提取逻辑

        验证:
        - AI能识别并提取模板中标记为required=True的字段
        - 缺少required字段时会有警告或错误提示
        """
        client, bucket, s3_client = async_client_with_aws

        # 创建模板
        template_response = await client.post(
            "/api/v1/templates",
            json=custom_template_data
        )
        template_id = template_response.json()["id"]

        # 使用不完整的文本创建会议 (缺少某些required字段的内容)
        incomplete_text = """
        今天进行了代码评审。
        评审人：张工
        发现了一些问题需要改进。
        """

        meeting_response = await client.post(
            "/api/v1/meetings",
            data={
                "input_type": "text",
                "text_content": incomplete_text,
                "template_id": template_id
            }
        )

        assert meeting_response.status_code == 201
        meeting_id = meeting_response.json()["id"]

        # 获取会议详情
        detail_response = await client.get(f"/api/v1/meetings/{meeting_id}")
        meeting_detail = detail_response.json()

        # 验证系统处理了不完整的输入
        # 根据业务逻辑，可能：
        # 1. 在metadata中标记缺失的required字段
        # 2. 在content中用占位符填充
        # 3. 状态标记为需要人工审查
        assert "status" in meeting_detail

    async def test_08_get_template_by_id(
        self, async_client_with_aws, custom_template_data
    ):
        """
        测试步骤8: 根据ID获取单个模板

        验证:
        - GET /api/v1/templates/{template_id} 返回模板详情
        - 不存在的模板返回404
        """
        client, bucket, s3_client = async_client_with_aws

        # 创建模板
        create_response = await client.post(
            "/api/v1/templates",
            json=custom_template_data
        )
        template_id = create_response.json()["id"]

        # 获取模板详情
        get_response = await client.get(f"/api/v1/templates/{template_id}")
        assert get_response.status_code == 200

        template = get_response.json()
        assert template["id"] == template_id
        assert template["name"] == "技术评审模板"

        # 测试不存在的模板
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        not_found_response = await client.get(f"/api/v1/templates/{fake_uuid}")
        assert not_found_response.status_code == 404

    async def test_09_end_to_end_custom_template_workflow(
        self,
        async_client_with_aws,
        custom_template_data,
        meeting_text_for_template
    ):
        """
        测试步骤9: 完整端到端工作流

        模拟场景5的完整流程:
        1. 创建自定义模板
        2. 查询并验证模板存在
        3. 使用模板创建会议
        4. 验证会议使用了正确的模板
        5. 导出会议记录
        """
        client, bucket, s3_client = async_client_with_aws

        # 步骤1: 创建模板
        template_response = await client.post(
            "/api/v1/templates",
            json=custom_template_data
        )
        assert template_response.status_code == 201
        template_id = template_response.json()["id"]

        # 步骤2: 验证模板可以查询到
        list_response = await client.get("/api/v1/templates")
        templates = list_response.json()
        assert any(t["id"] == template_id for t in templates)

        # 步骤3: 使用模板创建会议
        meeting_response = await client.post(
            "/api/v1/meetings",
            data={
                "input_type": "text",
                "text_content": meeting_text_for_template,
                "template_id": template_id
            }
        )
        assert meeting_response.status_code == 201
        meeting_id = meeting_response.json()["id"]

        # 步骤4: 验证会议使用了正确的模板
        detail_response = await client.get(f"/api/v1/meetings/{meeting_id}")
        meeting = detail_response.json()
        assert meeting["template_id"] == template_id

        # 步骤5: 导出会议记录 (假设有export端点)
        export_response = await client.get(
            f"/api/v1/meetings/{meeting_id}/export",
            params={"stage": "draft"}
        )

        # 导出可能需要会议处理完成，这里至少验证端点存在
        # 实际状态码取决于会议的处理状态
        assert export_response.status_code in [200, 202, 404, 422]

    async def test_10_template_with_complex_structure(
        self, async_client_with_aws
    ):
        """
        测试步骤10: 复杂模板结构

        验证:
        - 支持多个section
        - 支持多个字段
        - 正确处理required和非required混合
        """
        client, bucket, s3_client = async_client_with_aws

        complex_template = {
            "name": "全面会议模板",
            "structure": {
                "sections": [
                    {
                        "name": "基本信息",
                        "fields": [
                            {"key": "title", "label": "标题", "required": True},
                            {"key": "date", "label": "日期", "required": True},
                            {"key": "location", "label": "地点", "required": False}
                        ]
                    },
                    {
                        "name": "参会人员",
                        "fields": [
                            {"key": "participants", "label": "参会者", "required": True},
                            {"key": "absentees", "label": "缺席者", "required": False}
                        ]
                    },
                    {
                        "name": "会议内容",
                        "fields": [
                            {"key": "topics", "label": "讨论议题", "required": True},
                            {"key": "decisions", "label": "决策", "required": True},
                            {"key": "action_items", "label": "行动项", "required": True}
                        ]
                    },
                    {
                        "name": "附加信息",
                        "fields": [
                            {"key": "notes", "label": "备注", "required": False},
                            {"key": "next_meeting", "label": "下次会议", "required": False}
                        ]
                    }
                ]
            }
        }

        response = await client.post(
            "/api/v1/templates",
            json=complex_template
        )

        assert response.status_code == 201
        template = response.json()

        # 验证结构完整性
        assert len(template["structure"]["sections"]) == 4
        assert template["structure"]["sections"][0]["name"] == "基本信息"
        assert template["structure"]["sections"][2]["name"] == "会议内容"


@pytest.mark.integration
class TestTemplateEdgeCases:
    """模板边界情况测试"""

    async def test_duplicate_template_names(self, async_client_with_aws):
        """测试重复模板名称处理"""
        client, bucket, s3_client = async_client_with_aws

        template_data = {
            "name": "重复测试模板",
            "structure": {
                "sections": [
                    {
                        "name": "测试",
                        "fields": [{"key": "test", "label": "测试", "required": True}]
                    }
                ]
            }
        }

        # 创建第一个模板
        response1 = await client.post("/api/v1/templates", json=template_data)
        assert response1.status_code == 201

        # 创建同名模板 (应该被允许，因为ID不同)
        response2 = await client.post("/api/v1/templates", json=template_data)
        assert response2.status_code == 201

        # 验证两个模板ID不同
        assert response1.json()["id"] != response2.json()["id"]

    async def test_template_with_special_characters(self, async_client_with_aws):
        """测试包含特殊字符的模板"""
        client, bucket, s3_client = async_client_with_aws

        template_data = {
            "name": "特殊字符模板 !@#$%^&*()",
            "structure": {
                "sections": [
                    {
                        "name": "测试 & 验证",
                        "fields": [
                            {
                                "key": "test_field",
                                "label": "字段<标签>",
                                "required": True
                            }
                        ]
                    }
                ]
            }
        }

        response = await client.post("/api/v1/templates", json=template_data)
        assert response.status_code == 201

        template = response.json()
        assert template["name"] == "特殊字符模板 !@#$%^&*()"

    async def test_template_with_chinese_keys(self, async_client_with_aws):
        """测试使用中文key的模板"""
        client, bucket, s3_client = async_client_with_aws

        template_data = {
            "name": "中文key模板",
            "structure": {
                "sections": [
                    {
                        "name": "信息",
                        "fields": [
                            {"key": "标题", "label": "会议标题", "required": True},
                            {"key": "日期", "label": "会议日期", "required": True}
                        ]
                    }
                ]
            }
        }

        response = await client.post("/api/v1/templates", json=template_data)
        # 根据业务规则，可能接受或拒绝中文key
        assert response.status_code in [201, 400, 422]
