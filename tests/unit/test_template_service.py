"""
Template Service单元测试

测试TemplateService的渲染、验证和格式化功能
覆盖所有主要代码路径以提升覆盖率
"""

import pytest
from datetime import datetime, UTC
from src.services.template_service import TemplateService
from src.models.template import (
    Template,
    TemplateStructure,
    TemplateSection,
    TemplateField,
    DEFAULT_TEMPLATE,
)


@pytest.mark.unit
class TestTemplateService:
    """TemplateService单元测试"""

    @pytest.fixture
    def service(self):
        """创建TemplateService实例"""
        return TemplateService()

    @pytest.fixture
    def simple_template(self):
        """简单测试模板"""
        return Template(
            id="test-001",
            name="测试模板",
            is_default=False,
            created_at=datetime.now(UTC),
            structure=TemplateStructure(
                sections=[
                    TemplateSection(
                        name="基本信息",
                        fields=[
                            TemplateField(key="title", label="标题", required=True),
                            TemplateField(key="date", label="日期", required=True),
                            TemplateField(key="optional", label="可选字段", required=False),
                        ],
                    ),
                    TemplateSection(
                        name="详细内容",
                        fields=[
                            TemplateField(key="topics", label="议题", required=False),
                            TemplateField(key="decisions", label="决策", required=False),
                        ],
                    ),
                ]
            ),
        )

    @pytest.fixture
    def complete_data(self):
        """完整的测试数据"""
        return {
            "title": "Q4产品规划会议",
            "date": "2025-10-01",
            "optional": "备注信息",
            "topics": ["AI功能开发", "性能优化", "用户体验改进"],
            "decisions": ["优先开发AI功能", "下周开始性能优化"],
        }

    async def test_render_template_with_complete_data(self, service, simple_template, complete_data):
        """测试使用完整数据渲染模板"""
        markdown = await service.render_template(simple_template, complete_data)

        # 验证基本结构
        assert "# 会议记录" in markdown
        assert "## 基本信息" in markdown
        assert "## 详细内容" in markdown

        # 验证必填字段
        assert "**标题**: Q4产品规划会议" in markdown
        assert "**日期**: 2025-10-01" in markdown

        # 验证可选字段
        assert "**可选字段**: 备注信息" in markdown

        # 验证列表字段
        assert "**议题**:" in markdown
        assert "- AI功能开发" in markdown
        assert "- 性能优化" in markdown
        assert "- 用户体验改进" in markdown

        assert "**决策**:" in markdown
        assert "- 优先开发AI功能" in markdown
        assert "- 下周开始性能优化" in markdown

    async def test_render_template_with_minimal_data(self, service, simple_template):
        """测试使用最小数据渲染模板（仅必填字段）"""
        minimal_data = {
            "title": "简单会议",
            "date": "2025-10-02",
        }

        markdown = await service.render_template(simple_template, minimal_data)

        # 验证包含必填字段
        assert "**标题**: 简单会议" in markdown
        assert "**日期**: 2025-10-02" in markdown

        # 验证没有可选字段章节（因为没有数据）
        # 只有包含数据的字段才会显示

    async def test_render_template_missing_required_field(self, service, simple_template):
        """测试缺少必填字段时抛出异常"""
        incomplete_data = {
            "title": "会议标题",
            # 缺少必需的date字段
        }

        with pytest.raises(ValueError, match="缺少必需字段"):
            await service.render_template(simple_template, incomplete_data)

    async def test_validate_extracted_data_success(self, service, simple_template):
        """测试数据验证通过"""
        valid_data = {
            "title": "会议",
            "date": "2025-10-01",
        }

        # 不应抛出异常
        await service.validate_extracted_data(simple_template, valid_data)

    async def test_validate_extracted_data_missing_multiple_fields(self, service, simple_template):
        """测试缺少多个必填字段"""
        invalid_data = {}

        with pytest.raises(ValueError) as exc_info:
            await service.validate_extracted_data(simple_template, invalid_data)

        error_msg = str(exc_info.value)
        assert "title" in error_msg
        assert "date" in error_msg

    async def test_format_field_value_string(self, service):
        """测试格式化字符串值"""
        result = service._format_field_value("简单文本")
        assert result == "简单文本"

    async def test_format_field_value_none(self, service):
        """测试格式化None值"""
        result = service._format_field_value(None)
        assert result == ""

    async def test_format_field_value_empty_list(self, service):
        """测试格式化空列表"""
        result = service._format_field_value([])
        assert result == ""

    async def test_format_field_value_string_list(self, service):
        """测试格式化字符串列表"""
        result = service._format_field_value(["项目1", "项目2", "项目3"])
        assert result == "- 项目1\n- 项目2\n- 项目3"

    async def test_format_field_value_dict_list(self, service):
        """测试格式化字典列表"""
        dict_list = [
            {"任务": "开发功能A", "负责人": "张三", "截止日期": "2025-10-15"},
            {"任务": "测试功能B", "负责人": "李四", "截止日期": "2025-10-20"},
        ]

        result = service._format_field_value(dict_list)

        # 验证格式
        assert "- 任务: 开发功能A | 负责人: 张三" in result
        assert "- 任务: 测试功能B | 负责人: 李四" in result

    async def test_format_field_value_dict_list_with_nested_list(self, service):
        """测试格式化包含嵌套列表的字典列表"""
        dict_list = [
            {"任务": "开发", "子任务": ["设计", "编码", "测试"]},
            {"任务": "部署", "子任务": ["构建", "发布"]},
        ]

        result = service._format_field_value(dict_list)

        # 验证嵌套列表被正确格式化
        assert "- 任务: 开发" in result
        assert "子任务: 设计, 编码, 测试" in result
        assert "- 任务: 部署" in result
        assert "子任务: 构建, 发布" in result

    async def test_format_field_value_simple_dict(self, service):
        """测试格式化简单字典（少于3个键值对）"""
        simple_dict = {"状态": "进行中", "优先级": "高"}

        result = service._format_field_value(simple_dict)
        assert result == "状态: 进行中, 优先级: 高"

    async def test_format_field_value_complex_dict(self, service):
        """测试格式化复杂字典（使用JSON格式）"""
        complex_dict = {
            "项目": "AI会议助手",
            "阶段": "开发",
            "团队": {"前端": 3, "后端": 4, "测试": 2},
            "预算": 100000,
        }

        result = service._format_field_value(complex_dict)

        # 应该包含JSON代码块
        assert "```json" in result
        assert '"项目": "AI会议助手"' in result or '"项目":"AI会议助手"' in result

    async def test_format_field_value_boolean(self, service):
        """测试格式化布尔值"""
        assert service._format_field_value(True) == "是"
        assert service._format_field_value(False) == "否"

    async def test_format_field_value_number(self, service):
        """测试格式化数字"""
        assert service._format_field_value(42) == "42"
        assert service._format_field_value(3.14) == "3.14"
        assert service._format_field_value(0) == "0"

    async def test_format_simple_value_bool(self, service):
        """测试_format_simple_value处理布尔值"""
        assert service._format_simple_value(True) == "是"
        assert service._format_simple_value(False) == "否"

    async def test_format_simple_value_int(self, service):
        """测试_format_simple_value处理整数"""
        assert service._format_simple_value(100) == "100"
        assert service._format_simple_value(-5) == "-5"

    async def test_format_simple_value_float(self, service):
        """测试_format_simple_value处理浮点数"""
        assert service._format_simple_value(3.14159) == "3.14159"
        assert service._format_simple_value(0.0) == "0.0"

    async def test_format_simple_value_string(self, service):
        """测试_format_simple_value处理字符串"""
        assert service._format_simple_value("测试") == "测试"
        assert service._format_simple_value("") == ""

    async def test_render_section_with_no_data(self, service):
        """测试渲染没有数据的章节（返回空字符串）"""
        section = TemplateSection(
            name="空章节",
            fields=[
                TemplateField(key="missing_field", label="缺失字段", required=False),
            ],
        )

        result = service._render_section(section, {})
        assert result == ""

    async def test_render_section_with_none_values(self, service):
        """测试渲染包含None值的章节"""
        section = TemplateSection(
            name="测试章节",
            fields=[
                TemplateField(key="field1", label="字段1", required=False),
                TemplateField(key="field2", label="字段2", required=False),
            ],
        )

        data = {"field1": None, "field2": "有效值"}

        result = service._render_section(section, data)

        # None值应该被跳过
        assert "字段1" not in result
        assert "**字段2**: 有效值" in result

    async def test_render_section_with_empty_string(self, service):
        """测试渲染包含空字符串的章节"""
        section = TemplateSection(
            name="测试章节",
            fields=[
                TemplateField(key="empty_field", label="空字段", required=False),
            ],
        )

        data = {"empty_field": ""}

        result = service._render_section(section, data)

        # 空字符串应该被跳过
        assert result == ""

    async def test_render_section_with_multiline_content(self, service):
        """测试渲染多行内容"""
        section = TemplateSection(
            name="测试章节",
            fields=[
                TemplateField(key="items", label="项目列表", required=False),
            ],
        )

        data = {"items": ["项目A", "项目B", "项目C"]}

        result = service._render_section(section, data)

        # 多行内容应该标签后换行
        assert "**项目列表**:\n" in result
        assert "- 项目A" in result

    async def test_render_section_single_line_format(self, service):
        """测试渲染单行内容格式"""
        section = TemplateSection(
            name="测试章节",
            fields=[
                TemplateField(key="title", label="标题", required=False),
            ],
        )

        data = {"title": "单行文本"}

        result = service._render_section(section, data)

        # 单行内容应该使用行内格式
        assert "**标题**: 单行文本" in result

    async def test_render_template_with_default_template(self, service):
        """测试使用默认模板渲染"""
        data = {
            "title": "产品规划会议",
            "date": "2025-10-01",
            "participants": "张三、李四、王五",
            "topics": ["功能规划", "时间安排"],
            "decisions": ["确定开发优先级"],
            "action_items": ["张三负责需求文档", "李四负责技术方案"],
        }

        markdown = await service.render_template(DEFAULT_TEMPLATE, data)

        # 验证基本结构
        assert "# 会议记录" in markdown
        assert "## 会议基本信息" in markdown
        assert "## 会议内容" in markdown

        # 验证所有字段
        assert "产品规划会议" in markdown
        assert "2025-10-01" in markdown
        assert "张三、李四、王五" in markdown
        assert "功能规划" in markdown
        assert "确定开发优先级" in markdown
        assert "张三负责需求文档" in markdown

    async def test_render_template_no_trailing_blank_lines(self, service, simple_template):
        """测试渲染结果没有末尾多余空行"""
        data = {"title": "测试", "date": "2025-10-01"}

        markdown = await service.render_template(simple_template, data)

        # 验证末尾没有多余的空行
        assert not markdown.endswith("\n\n")
        assert markdown.endswith("\n") or not markdown.endswith(" ")

    async def test_validate_extracted_data_with_extra_fields(self, service, simple_template):
        """测试验证数据时允许额外字段"""
        data_with_extra = {
            "title": "会议",
            "date": "2025-10-01",
            "extra_field": "额外数据",  # 额外字段应该被忽略
        }

        # 不应抛出异常
        await service.validate_extracted_data(simple_template, data_with_extra)

    async def test_format_field_value_mixed_list(self, service):
        """测试格式化包含不同类型的列表"""
        mixed_list = ["文本", 123, True]

        result = service._format_field_value(mixed_list)

        # 所有元素应该被转换为字符串
        assert "- 文本" in result
        assert "- 123" in result
        assert "- 是" in result

    async def test_render_section_all_fields_present(self, service):
        """测试渲染所有字段都存在的章节"""
        section = TemplateSection(
            name="完整章节",
            fields=[
                TemplateField(key="f1", label="字段1", required=True),
                TemplateField(key="f2", label="字段2", required=True),
                TemplateField(key="f3", label="字段3", required=False),
            ],
        )

        data = {
            "f1": "值1",
            "f2": "值2",
            "f3": "值3",
        }

        result = service._render_section(section, data)

        assert "## 完整章节" in result
        assert "**字段1**: 值1" in result
        assert "**字段2**: 值2" in result
        assert "**字段3**: 值3" in result

    async def test_render_template_multiple_sections_some_empty(self, service):
        """测试渲染多个章节，其中一些没有数据"""
        template = Template(
            id="test-002",
            name="测试模板",
            is_default=False,
            created_at=datetime.now(UTC),
            structure=TemplateStructure(
                sections=[
                    TemplateSection(
                        name="有数据的章节",
                        fields=[
                            TemplateField(key="field1", label="字段1", required=True),
                        ],
                    ),
                    TemplateSection(
                        name="没有数据的章节",
                        fields=[
                            TemplateField(key="field2", label="字段2", required=False),
                        ],
                    ),
                    TemplateSection(
                        name="另一个有数据的章节",
                        fields=[
                            TemplateField(key="field3", label="字段3", required=False),
                        ],
                    ),
                ]
            ),
        )

        data = {
            "field1": "数据1",
            "field3": "数据3",
            # field2没有提供
        }

        markdown = await service.render_template(template, data)

        # 有数据的章节应该出现
        assert "## 有数据的章节" in markdown
        assert "## 另一个有数据的章节" in markdown

        # 没有数据的章节不应该出现
        assert "## 没有数据的章节" not in markdown
