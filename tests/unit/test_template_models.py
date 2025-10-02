"""
Template模型单元测试

测试src/models/template.py中定义的所有Pydantic模型。
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models.template import (
    DEFAULT_TEMPLATE,
    DEFAULT_TEMPLATE_STRUCTURE,
    EXAMPLE_TECH_REVIEW_TEMPLATE,
    Template,
    TemplateField,
    TemplateInput,
    TemplateSection,
    TemplateStructure,
)


class TestTemplateField:
    """TemplateField模型测试"""

    def test_create_required_field(self):
        """测试创建必填字段"""
        field = TemplateField(key="title", label="会议主题", required=True)
        assert field.key == "title"
        assert field.label == "会议主题"
        assert field.required is True

    def test_create_optional_field(self):
        """测试创建可选字段(默认required=False)"""
        field = TemplateField(key="notes", label="备注")
        assert field.key == "notes"
        assert field.label == "备注"
        assert field.required is False

    def test_field_serialization(self):
        """测试字段序列化"""
        field = TemplateField(key="date", label="日期", required=True)
        data = field.model_dump()
        assert data == {"key": "date", "label": "日期", "required": True}

    def test_field_deserialization(self):
        """测试字段反序列化"""
        data = {"key": "location", "label": "地点", "required": False}
        field = TemplateField(**data)
        assert field.key == "location"
        assert field.label == "地点"
        assert field.required is False


class TestTemplateSection:
    """TemplateSection模型测试"""

    def test_create_section_with_fields(self):
        """测试创建包含字段的section"""
        section = TemplateSection(
            name="基本信息",
            fields=[
                TemplateField(key="title", label="标题", required=True),
                TemplateField(key="date", label="日期", required=False),
            ],
        )
        assert section.name == "基本信息"
        assert len(section.fields) == 2
        assert section.fields[0].key == "title"
        assert section.fields[1].key == "date"

    def test_section_requires_at_least_one_field(self):
        """测试section必须至少有一个字段"""
        with pytest.raises(ValidationError) as exc_info:
            TemplateSection(name="空章节", fields=[])

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "too_short"
        assert "at least 1 item" in errors[0]["msg"]

    def test_section_serialization(self):
        """测试section序列化"""
        section = TemplateSection(
            name="会议内容",
            fields=[TemplateField(key="topics", label="议题", required=True)],
        )
        data = section.model_dump()
        assert data["name"] == "会议内容"
        assert len(data["fields"]) == 1
        assert data["fields"][0]["key"] == "topics"


class TestTemplateStructure:
    """TemplateStructure模型测试"""

    def test_create_structure_with_sections(self):
        """测试创建包含sections的结构"""
        structure = TemplateStructure(
            sections=[
                TemplateSection(
                    name="section1",
                    fields=[TemplateField(key="key1", label="label1")],
                )
            ]
        )
        assert len(structure.sections) == 1
        assert structure.sections[0].name == "section1"

    def test_structure_requires_at_least_one_section(self):
        """测试structure必须至少有一个section"""
        with pytest.raises(ValidationError) as exc_info:
            TemplateStructure(sections=[])

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "too_short"

    def test_structure_with_multiple_sections(self):
        """测试多个sections的结构"""
        structure = TemplateStructure(
            sections=[
                TemplateSection(
                    name="section1",
                    fields=[TemplateField(key="k1", label="l1")],
                ),
                TemplateSection(
                    name="section2",
                    fields=[TemplateField(key="k2", label="l2")],
                ),
            ]
        )
        assert len(structure.sections) == 2


class TestTemplate:
    """Template主模型测试"""

    def test_create_valid_template(self):
        """测试创建有效模板"""
        template = Template(
            id="test-id",
            name="测试模板",
            is_default=False,
            created_at=datetime(2025, 10, 1, 12, 0, 0),
            creator_identifier="user123",
            structure=DEFAULT_TEMPLATE_STRUCTURE,
        )
        assert template.id == "test-id"
        assert template.name == "测试模板"
        assert template.is_default is False
        assert template.creator_identifier == "user123"
        assert len(template.structure.sections) == 2

    def test_template_default_values(self):
        """测试模板默认值"""
        template = Template(
            id="test",
            name="test",
            created_at=datetime.now(),
            structure=DEFAULT_TEMPLATE_STRUCTURE,
        )
        assert template.is_default is False
        assert template.creator_identifier is None

    def test_template_name_max_length(self):
        """测试模板名称最大长度限制"""
        long_name = "x" * 101  # 超过100字符
        with pytest.raises(ValidationError) as exc_info:
            Template(
                id="test",
                name=long_name,
                created_at=datetime.now(),
                structure=DEFAULT_TEMPLATE_STRUCTURE,
            )

        errors = exc_info.value.errors()
        assert any("at most 100 characters" in str(e) for e in errors)

    def test_template_structure_validation(self):
        """测试模板结构验证器"""
        # 创建空structure应该在TemplateStructure层面失败
        with pytest.raises(ValidationError):
            Template(
                id="invalid",
                name="无效模板",
                created_at=datetime.now(),
                structure=TemplateStructure(sections=[]),
            )

    def test_template_serialization(self):
        """测试模板序列化"""
        template = Template(
            id="test-id",
            name="测试",
            is_default=True,
            created_at=datetime(2025, 10, 1),
            structure=DEFAULT_TEMPLATE_STRUCTURE,
        )
        data = template.model_dump()
        assert data["id"] == "test-id"
        assert data["name"] == "测试"
        assert data["is_default"] is True
        assert "structure" in data
        assert "sections" in data["structure"]

    def test_template_json_serialization(self):
        """测试模板JSON序列化"""
        template = DEFAULT_TEMPLATE
        json_str = template.model_dump_json()
        assert '"id":"default"' in json_str
        assert '"name":"标准会议记录模板"' in json_str
        assert '"is_default":true' in json_str


class TestTemplateInput:
    """TemplateInput模型测试"""

    def test_create_template_input(self):
        """测试创建模板输入"""
        input_data = TemplateInput(
            name="新模板", structure=DEFAULT_TEMPLATE_STRUCTURE
        )
        assert input_data.name == "新模板"
        assert len(input_data.structure.sections) == 2

    def test_template_input_name_validation(self):
        """测试输入模板名称验证"""
        long_name = "x" * 101
        with pytest.raises(ValidationError):
            TemplateInput(name=long_name, structure=DEFAULT_TEMPLATE_STRUCTURE)

    def test_template_input_serialization(self):
        """测试输入模板序列化"""
        input_data = TemplateInput(
            name="测试", structure=DEFAULT_TEMPLATE_STRUCTURE
        )
        data = input_data.model_dump()
        assert "name" in data
        assert "structure" in data
        assert "id" not in data  # TemplateInput不包含id
        assert "created_at" not in data  # TemplateInput不包含created_at


class TestDefaultTemplateStructure:
    """默认模板结构测试"""

    def test_default_structure_has_two_sections(self):
        """测试默认结构有两个sections"""
        assert len(DEFAULT_TEMPLATE_STRUCTURE.sections) == 2

    def test_default_structure_section_names(self):
        """测试默认结构section名称"""
        section_names = [s.name for s in DEFAULT_TEMPLATE_STRUCTURE.sections]
        assert "会议基本信息" in section_names
        assert "会议内容" in section_names

    def test_default_structure_basic_info_fields(self):
        """测试基本信息section的字段"""
        basic_info = DEFAULT_TEMPLATE_STRUCTURE.sections[0]
        assert basic_info.name == "会议基本信息"
        field_keys = [f.key for f in basic_info.fields]
        assert "title" in field_keys
        assert "date" in field_keys
        assert "participants" in field_keys

    def test_default_structure_content_fields(self):
        """测试会议内容section的字段"""
        content = DEFAULT_TEMPLATE_STRUCTURE.sections[1]
        assert content.name == "会议内容"
        field_keys = [f.key for f in content.fields]
        assert "topics" in field_keys
        assert "decisions" in field_keys
        assert "action_items" in field_keys

    def test_default_structure_required_fields(self):
        """测试默认结构的必填字段"""
        all_fields = []
        for section in DEFAULT_TEMPLATE_STRUCTURE.sections:
            all_fields.extend(section.fields)

        required_fields = [f.key for f in all_fields if f.required]
        assert "title" in required_fields
        assert "date" in required_fields
        assert "topics" in required_fields


class TestDefaultTemplate:
    """默认模板测试"""

    def test_default_template_properties(self):
        """测试默认模板属性"""
        assert DEFAULT_TEMPLATE.id == "default"
        assert DEFAULT_TEMPLATE.name == "标准会议记录模板"
        assert DEFAULT_TEMPLATE.is_default is True
        assert DEFAULT_TEMPLATE.creator_identifier is None

    def test_default_template_structure(self):
        """测试默认模板结构"""
        assert DEFAULT_TEMPLATE.structure == DEFAULT_TEMPLATE_STRUCTURE

    def test_default_template_created_at(self):
        """测试默认模板创建时间"""
        assert DEFAULT_TEMPLATE.created_at == datetime(2025, 10, 1, 0, 0, 0)


class TestExampleTechReviewTemplate:
    """技术评审模板示例测试"""

    def test_tech_review_template_properties(self):
        """测试技术评审模板属性"""
        assert EXAMPLE_TECH_REVIEW_TEMPLATE.id == "tech-review-v1"
        assert EXAMPLE_TECH_REVIEW_TEMPLATE.name == "技术评审模板"
        assert EXAMPLE_TECH_REVIEW_TEMPLATE.is_default is False
        assert EXAMPLE_TECH_REVIEW_TEMPLATE.creator_identifier == "user123"

    def test_tech_review_template_has_three_sections(self):
        """测试技术评审模板有三个sections"""
        assert len(EXAMPLE_TECH_REVIEW_TEMPLATE.structure.sections) == 3

    def test_tech_review_template_section_names(self):
        """测试技术评审模板section名称"""
        section_names = [
            s.name for s in EXAMPLE_TECH_REVIEW_TEMPLATE.structure.sections
        ]
        assert "评审基本信息" in section_names
        assert "技术方案" in section_names
        assert "评审结论" in section_names

    def test_tech_review_template_field_counts(self):
        """测试技术评审模板各section字段数量"""
        sections = EXAMPLE_TECH_REVIEW_TEMPLATE.structure.sections
        assert len(sections[0].fields) == 4  # 评审基本信息
        assert len(sections[1].fields) == 3  # 技术方案
        assert len(sections[2].fields) == 3  # 评审结论


class TestEdgeCases:
    """边界情况测试"""

    def test_unicode_field_labels(self):
        """测试Unicode字段标签"""
        field = TemplateField(key="emoji", label="测试 🎉 emoji", required=False)
        assert "🎉" in field.label

    def test_nested_model_validation(self):
        """测试嵌套模型验证"""
        # 完整的嵌套结构应该成功
        template = Template(
            id="nested",
            name="嵌套测试",
            created_at=datetime.now(),
            structure=TemplateStructure(
                sections=[
                    TemplateSection(
                        name="s1",
                        fields=[TemplateField(key="k1", label="l1")],
                    )
                ]
            ),
        )
        assert template.id == "nested"

    def test_template_with_many_sections(self):
        """测试包含多个sections的模板"""
        sections = [
            TemplateSection(
                name=f"section{i}",
                fields=[TemplateField(key=f"key{i}", label=f"label{i}")],
            )
            for i in range(10)
        ]
        structure = TemplateStructure(sections=sections)
        template = Template(
            id="many-sections",
            name="多section模板",
            created_at=datetime.now(),
            structure=structure,
        )
        assert len(template.structure.sections) == 10

    def test_template_with_many_fields_in_section(self):
        """测试section包含多个fields"""
        fields = [
            TemplateField(key=f"key{i}", label=f"label{i}", required=i % 2 == 0)
            for i in range(20)
        ]
        section = TemplateSection(name="large-section", fields=fields)
        assert len(section.fields) == 20
        required_count = sum(1 for f in section.fields if f.required)
        assert required_count == 10
