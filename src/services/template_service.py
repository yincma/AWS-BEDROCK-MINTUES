"""
模板引擎服务

负责将AI提取的JSON数据渲染成符合模板结构的Markdown格式。
支持多种数据类型的格式化，并确保生成美观的Markdown文档。
"""

import json
from typing import Any, Dict, List

from src.models.template import Template, TemplateSection, TemplateField


class TemplateService:
    """
    模板引擎服务类

    提供模板渲染和数据验证功能，将结构化数据转换为Markdown格式的会议记录。
    """

    async def render_template(
        self,
        template: Template,
        extracted_data: Dict[str, Any]
    ) -> str:
        """
        根据模板和提取的数据渲染Markdown

        Args:
            template: Template对象，定义文档结构
            extracted_data: AI提取的数据字典
                例如: {
                    "title": "Q4产品规划",
                    "date": "2025-10-01",
                    "topics": ["AI功能", "性能优化"],
                    "decisions": ["优先AI"],
                    "action_items": ["张三完成PRD"]
                }

        Returns:
            str: 格式化的Markdown文本

        Raises:
            ValueError: 当缺少必需字段时

        Examples:
            >>> template = DEFAULT_TEMPLATE
            >>> data = {"title": "会议", "date": "2025-10-01", "topics": ["主题1"]}
            >>> markdown = await service.render_template(template, data)
            >>> print(markdown)
            # 会议记录

            ## 会议基本信息
            **会议主题**: 会议
            **会议日期**: 2025-10-01
            ...
        """
        # 验证必需字段
        await self.validate_extracted_data(template, extracted_data)

        # 构建Markdown文档
        markdown_lines = []

        # 添加文档标题
        markdown_lines.append("# 会议记录")
        markdown_lines.append("")  # 空行

        # 渲染每个章节
        for section in template.structure.sections:
            section_markdown = self._render_section(section, extracted_data)
            if section_markdown:  # 只添加非空章节
                markdown_lines.append(section_markdown)
                markdown_lines.append("")  # 章节之间添加空行

        # 移除末尾多余的空行并返回
        return "\n".join(markdown_lines).rstrip()

    async def validate_extracted_data(
        self,
        template: Template,
        extracted_data: Dict[str, Any]
    ) -> None:
        """
        验证提取的数据包含所有必需字段

        Args:
            template: 模板对象
            extracted_data: 提取的数据字典

        Raises:
            ValueError: 缺少必需字段时抛出异常

        Examples:
            >>> template = DEFAULT_TEMPLATE
            >>> data = {"title": "会议"}  # 缺少必需的date和topics
            >>> await service.validate_extracted_data(template, data)
            ValueError: 缺少必需字段: date, topics
        """
        # 收集所有必需字段的键名
        required_keys = [
            field.key
            for section in template.structure.sections
            for field in section.fields
            if field.required
        ]

        # 检查缺失的必需字段
        missing = [key for key in required_keys if key not in extracted_data]

        if missing:
            raise ValueError(f"缺少必需字段: {', '.join(missing)}")

    def _render_section(
        self,
        section: TemplateSection,
        data: Dict[str, Any]
    ) -> str:
        """
        渲染单个章节为Markdown

        Args:
            section: 章节定义
            data: 数据字典

        Returns:
            str: 章节的Markdown文本，如果章节没有任何数据则返回空字符串
        """
        # 收集章节内容
        content_lines = []

        # 遍历字段
        for field in section.fields:
            if field.key in data:
                value = data[field.key]
                # 跳过None或空值
                if value is None or (isinstance(value, (list, str)) and not value):
                    continue

                # 格式化字段值
                formatted_value = self._format_field_value(value)

                # 根据值的类型决定格式
                if '\n' in formatted_value:
                    # 多行内容：标签后换行，内容缩进或使用列表
                    content_lines.append(f"**{field.label}**:")
                    content_lines.append(formatted_value)
                else:
                    # 单行内容：使用行内格式
                    content_lines.append(f"**{field.label}**: {formatted_value}")

        # 如果章节没有任何内容，返回空字符串
        if not content_lines:
            return ""

        # 构建章节
        section_lines = [f"## {section.name}"]
        section_lines.extend(content_lines)

        return "\n".join(section_lines)

    def _format_field_value(self, value: Any) -> str:
        """
        格式化字段值为Markdown

        将不同类型的数据格式化为适合Markdown显示的字符串。

        Args:
            value: 任意类型的值

        Returns:
            str: 格式化后的字符串

        Examples:
            >>> service._format_field_value("简单文本")
            '简单文本'
            >>> service._format_field_value(["项目1", "项目2"])
            '- 项目1\\n- 项目2'
            >>> service._format_field_value({"key": "value"})
            '{\\n  "key": "value"\\n}'
        """
        if value is None:
            return ""

        if isinstance(value, list):
            # 列表转换为Markdown项目列表
            if not value:
                return ""

            # 检查列表项的类型
            if all(isinstance(item, dict) for item in value):
                # 字典列表：每个字典渲染为独立的项目
                formatted_items = []
                for item in value:
                    # 简化的字典显示
                    item_parts = []
                    for k, v in item.items():
                        if isinstance(v, list):
                            # 嵌套列表
                            sub_list = ", ".join(str(sub) for sub in v)
                            item_parts.append(f"{k}: {sub_list}")
                        else:
                            item_parts.append(f"{k}: {v}")
                    formatted_items.append(f"- {' | '.join(item_parts)}")
                return "\n".join(formatted_items)
            else:
                # 简单列表
                return "\n".join(f"- {self._format_simple_value(item)}" for item in value)

        elif isinstance(value, dict):
            # 字典格式化为JSON（用于调试或复杂对象）
            # 对于简单的键值对，可以格式化为更友好的格式
            if len(value) <= 3 and all(isinstance(v, (str, int, float, bool)) for v in value.values()):
                # 简单字典：使用行内格式
                items = [f"{k}: {v}" for k, v in value.items()]
                return ", ".join(items)
            else:
                # 复杂字典：使用JSON格式
                return f"```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```"

        else:
            # 其他类型：转换为字符串
            return self._format_simple_value(value)

    def _format_simple_value(self, value: Any) -> str:
        """
        格式化简单值为字符串

        Args:
            value: 简单类型的值

        Returns:
            str: 格式化后的字符串
        """
        if isinstance(value, bool):
            return "是" if value else "否"
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            return str(value)


# 导出
__all__ = ['TemplateService']