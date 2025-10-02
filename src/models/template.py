"""
Template模型定义

提供会议记录模板相关的Pydantic模型,支持自定义会议记录结构。
"""

from datetime import datetime
from typing import Optional

from typing import List
from pydantic import BaseModel, Field, field_validator


class TemplateField(BaseModel):
    """
    模板字段定义

    表示模板中每个section内的一个字段,如"会议主题"、"参与者"等。

    Attributes:
        key: 字段键名,用于程序识别
        label: 字段显示标签,用于UI显示
        required: 是否为必填字段,默认False

    Examples:
        >>> field = TemplateField(key="title", label="会议主题", required=True)
        >>> field.key
        'title'
        >>> field.required
        True
    """

    key: str = Field(description="字段键名")
    label: str = Field(description="字段显示标签")
    required: bool = False


class TemplateSection(BaseModel):
    """
    模板章节定义

    表示模板中的一个章节,如"会议基本信息"、"会议内容"等。
    每个章节包含多个字段。

    Attributes:
        name: 章节名称
        fields: 字段列表,至少包含一个字段

    Examples:
        >>> section = TemplateSection(
        ...     name="会议基本信息",
        ...     fields=[
        ...         TemplateField(key="title", label="会议主题", required=True)
        ...     ]
        ... )
        >>> section.name
        '会议基本信息'
        >>> len(section.fields)
        1
    """

    name: str = Field(description="章节名称")
    fields: List[TemplateField] = Field(description="字段列表", min_length=1)


class TemplateStructure(BaseModel):
    """
    模板结构定义

    定义完整的模板结构,包含所有章节。

    Attributes:
        sections: 章节列表,至少包含一个章节

    Examples:
        >>> structure = TemplateStructure(
        ...     sections=[
        ...         TemplateSection(
        ...             name="会议基本信息",
        ...             fields=[
        ...                 TemplateField(key="title", label="会议主题", required=True)
        ...             ]
        ...         )
        ...     ]
        ... )
        >>> len(structure.sections)
        1
    """

    sections: List[TemplateSection] = Field(description="章节列表", min_length=1)


class Template(BaseModel):
    """
    会议记录模板主模型

    定义完整的会议记录模板,包含元数据和结构定义。

    Attributes:
        id: 模板唯一标识符
        name: 模板名称,最大100字符
        is_default: 是否为默认模板
        created_at: 创建时间
        creator_identifier: 创建者标识(预留字段)
        structure: 模板结构定义

    Examples:
        >>> template = Template(
        ...     id="default",
        ...     name="标准会议记录模板",
        ...     is_default=True,
        ...     created_at=datetime.now(),
        ...     structure=DEFAULT_TEMPLATE_STRUCTURE
        ... )
        >>> template.is_default
        True
    """

    id: str
    name: str = Field(max_length=100)
    is_default: bool = False
    created_at: datetime
    creator_identifier: Optional[str] = None
    structure: TemplateStructure

    @field_validator('structure')
    @classmethod
    def validate_structure(cls, v):
        """
        验证模板结构完整性

        确保模板至少包含一个section。

        Raises:
            ValueError: 当模板没有任何section时

        Returns:
            v: 验证通过的模板结构
        """
        if not v.sections:
            raise ValueError("template必须至少有一个section")
        return v


class TemplateInput(BaseModel):
    """
    模板创建输入模型

    用于API POST /templates的请求体,不包含系统生成的字段。

    Attributes:
        name: 模板名称,最大100字符
        structure: 模板结构定义

    Examples:
        >>> input_data = TemplateInput(
        ...     name="我的自定义模板",
        ...     structure=TemplateStructure(
        ...         sections=[
        ...             TemplateSection(
        ...                 name="基本信息",
        ...                 fields=[
        ...                     TemplateField(key="title", label="标题", required=True)
        ...                 ]
        ...             )
        ...         ]
        ...     )
        ... )
        >>> input_data.name
        '我的自定义模板'
    """

    name: str = Field(max_length=100)
    structure: TemplateStructure


DEFAULT_TEMPLATE_STRUCTURE = TemplateStructure(
    sections=[
        TemplateSection(
            name="会议基本信息",
            fields=[
                TemplateField(key="title", label="会议主题", required=True),
                TemplateField(key="date", label="会议日期", required=True),
                TemplateField(key="participants", label="参与者", required=False),
            ],
        ),
        TemplateSection(
            name="会议内容",
            fields=[
                TemplateField(key="topics", label="讨论议题", required=True),
                TemplateField(key="decisions", label="决策事项", required=False),
                TemplateField(key="action_items", label="行动项", required=False),
            ],
        ),
    ]
)


DEFAULT_TEMPLATE = Template(
    id="default",
    name="标准会议记录模板",
    is_default=True,
    created_at=datetime(2025, 10, 1, 0, 0, 0),
    creator_identifier=None,
    structure=DEFAULT_TEMPLATE_STRUCTURE,
)


EXAMPLE_TECH_REVIEW_TEMPLATE = Template(
    id="tech-review-v1",
    name="技术评审模板",
    is_default=False,
    created_at=datetime(2025, 10, 1, 10, 0, 0),
    creator_identifier="user123",
    structure=TemplateStructure(
        sections=[
            TemplateSection(
                name="评审基本信息",
                fields=[
                    TemplateField(key="project_name", label="项目名称", required=True),
                    TemplateField(key="review_date", label="评审日期", required=True),
                    TemplateField(key="reviewers", label="评审人员", required=True),
                    TemplateField(key="presenter", label="汇报人", required=True),
                ],
            ),
            TemplateSection(
                name="技术方案",
                fields=[
                    TemplateField(key="architecture", label="架构设计", required=True),
                    TemplateField(key="tech_stack", label="技术栈", required=True),
                    TemplateField(key="data_model", label="数据模型", required=False),
                ],
            ),
            TemplateSection(
                name="评审结论",
                fields=[
                    TemplateField(key="issues", label="发现问题", required=False),
                    TemplateField(key="suggestions", label="改进建议", required=False),
                    TemplateField(key="approval_status", label="通过状态", required=True),
                ],
            ),
        ]
    ),
)
