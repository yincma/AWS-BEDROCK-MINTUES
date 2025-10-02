"""
Prompt模板加载器
使用Jinja2加载和渲染prompt模板
"""

import os
import logging
from pathlib import Path
from typing import Optional
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound

logger = logging.getLogger(__name__)


class PromptLoader:
    """Prompt模板加载和渲染器"""

    def __init__(self, prompts_dir: Optional[str] = None):
        """
        初始化prompt加载器

        Args:
            prompts_dir: prompt模板目录路径
        """
        # 确定prompts目录
        if prompts_dir:
            self.prompts_dir = Path(prompts_dir)
        else:
            # 默认使用项目根目录下的prompts文件夹
            project_root = Path(__file__).parent.parent.parent
            self.prompts_dir = project_root / 'prompts'

        # 确保目录存在
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

        # 初始化Jinja2环境
        self.env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            trim_blocks=True,  # 移除块后的空行
            lstrip_blocks=True,  # 移除块前的空格
            keep_trailing_newline=True  # 保留文件末尾换行
        )

        logger.info(f"PromptLoader initialized with directory: {self.prompts_dir}")

    def load_template(self, template_name: str) -> Template:
        """
        加载prompt模板

        Args:
            template_name: 模板文件名

        Returns:
            Template: Jinja2模板对象

        Raises:
            FileNotFoundError: 模板文件不存在
        """
        try:
            template = self.env.get_template(template_name)
            logger.debug(f"Template loaded: {template_name}")
            return template

        except TemplateNotFound:
            error_msg = f"Template not found: {template_name} in {self.prompts_dir}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

    def render_template(
        self,
        template_name: str,
        **kwargs
    ) -> str:
        """
        加载并渲染prompt模板

        Args:
            template_name: 模板文件名
            **kwargs: 模板变量

        Returns:
            str: 渲染后的prompt文本
        """
        try:
            template = self.load_template(template_name)
            rendered = template.render(**kwargs)

            # 记录渲染信息
            logger.debug(
                f"Template rendered: {template_name}, "
                f"variables: {list(kwargs.keys())}, "
                f"output length: {len(rendered)} chars"
            )

            return rendered

        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            raise

    def list_templates(self) -> list[str]:
        """
        列出所有可用的prompt模板

        Returns:
            list[str]: 模板文件名列表
        """
        templates = []

        for file_path in self.prompts_dir.glob('*.txt'):
            templates.append(file_path.name)

        for file_path in self.prompts_dir.glob('*.j2'):
            templates.append(file_path.name)

        logger.info(f"Found {len(templates)} templates")
        return sorted(templates)

    def validate_template(self, template_name: str) -> bool:
        """
        验证模板是否存在且语法正确

        Args:
            template_name: 模板文件名

        Returns:
            bool: 模板是否有效
        """
        try:
            self.load_template(template_name)
            return True
        except Exception as e:
            logger.warning(f"Template validation failed for {template_name}: {e}")
            return False

    def get_template_path(self, template_name: str) -> Path:
        """
        获取模板文件的完整路径

        Args:
            template_name: 模板文件名

        Returns:
            Path: 模板文件路径
        """
        return self.prompts_dir / template_name