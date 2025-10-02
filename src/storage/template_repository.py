"""模板仓库"""
from typing import Optional, List
from datetime import datetime, timezone
from uuid import uuid4
from src.models.template import Template, DEFAULT_TEMPLATE
from src.storage.s3_client import S3ClientWrapper


class TemplateRepository:
    """
    模板仓库类

    负责模板的持久化和检索
    """

    def __init__(self, s3_client: S3ClientWrapper):
        """
        初始化模板仓库

        Args:
            s3_client: S3客户端实例
        """
        self.s3 = s3_client
        # 在初始化时确保默认模板存在
        self._ensure_default_template_task = None

    async def _ensure_default_template(self):
        """确保默认模板存在"""
        default_key = f"{S3ClientWrapper.TEMPLATES_PREFIX}default.json"
        if not await self.s3.exists(default_key):
            # 保存默认模板
            await self.save(DEFAULT_TEMPLATE)

    async def get(self, template_id: str) -> Optional[Template]:
        """
        获取模板

        Args:
            template_id: 模板ID

        Returns:
            Template实例或None
        """
        key = f"{S3ClientWrapper.TEMPLATES_PREFIX}{template_id}.json"
        data = await self.s3.get_json(key)

        if data is None:
            return None

        try:
            # 移除内部字段
            data.pop('__etag', None)
            return Template(**data)
        except Exception as e:
            raise ValueError(f"解析模板失败: {str(e)}")

    async def save(self, template: Template) -> None:
        """
        保存模板

        Args:
            template: 模板实例
        """
        key = f"{S3ClientWrapper.TEMPLATES_PREFIX}{template.id}.json"

        # 处理datetime序列化
        data = template.model_dump(mode='json')
        if isinstance(data.get('created_at'), datetime):
            data['created_at'] = data['created_at'].isoformat()

        # 保存到S3
        await self.s3.put_json(key, data)

    async def list_all(self) -> List[Template]:
        """
        列出所有模板

        Returns:
            模板列表
        """
        # 确保默认模板存在
        await self._ensure_default_template()

        keys = await self.s3.list_keys(S3ClientWrapper.TEMPLATES_PREFIX)
        templates = []

        for key in keys:
            # 跳过非JSON文件
            if not key.endswith('.json'):
                continue

            data = await self.s3.get_json(key)
            if data:
                try:
                    # 移除内部字段
                    data.pop('__etag', None)
                    template = Template(**data)
                    templates.append(template)
                except Exception as e:
                    # 记录错误但继续处理其他文件
                    print(f"警告: 无法解析文件 {key}: {str(e)}")
                    continue

        # 按创建时间降序排序，默认模板始终在前
        templates.sort(key=lambda t: (not t.is_default, t.created_at), reverse=True)
        return templates

    async def get_default(self) -> Optional[Template]:
        """
        获取默认模板

        Returns:
            默认模板或None
        """
        # 先尝试从S3获取
        default_template = await self.get("default")
        if default_template:
            return default_template

        # 如果不存在，创建默认模板
        await self.save(DEFAULT_TEMPLATE)
        return DEFAULT_TEMPLATE

    async def create(self, name: str, structure: dict) -> Template:
        """
        创建新模板

        Args:
            name: 模板名称
            structure: 模板结构

        Returns:
            创建的模板实例
        """
        # 生成新ID
        template_id = str(uuid4())

        # 创建模板实例
        template = Template(
            id=template_id,
            name=name,
            is_default=False,
            created_at=datetime.now(timezone.utc),
            creator_identifier=None,  # 预留字段
            structure=structure
        )

        # 保存到S3
        await self.save(template)
        return template

    async def delete(self, template_id: str) -> None:
        """
        删除模板

        Args:
            template_id: 模板ID

        Raises:
            ValueError: 尝试删除默认模板
        """
        # 不允许删除默认模板
        if template_id == "default":
            raise ValueError("不能删除默认模板")

        key = f"{S3ClientWrapper.TEMPLATES_PREFIX}{template_id}.json"
        await self.s3.delete(key)

    async def exists(self, template_id: str) -> bool:
        """
        检查模板是否存在

        Args:
            template_id: 模板ID

        Returns:
            True如果存在，False否则
        """
        key = f"{S3ClientWrapper.TEMPLATES_PREFIX}{template_id}.json"
        return await self.s3.exists(key)

    async def update(self, template_id: str, name: Optional[str] = None, structure: Optional[dict] = None) -> Template:
        """
        更新模板

        Args:
            template_id: 模板ID
            name: 新的模板名称（可选）
            structure: 新的模板结构（可选）

        Returns:
            更新后的模板实例

        Raises:
            ValueError: 模板不存在或尝试更新默认模板
        """
        # 不允许更新默认模板
        if template_id == "default":
            raise ValueError("不能修改默认模板")

        # 获取现有模板
        template = await self.get(template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")

        # 更新字段
        if name is not None:
            template.name = name
        if structure is not None:
            template.structure = structure

        # 保存更新
        await self.save(template)
        return template

    async def list_user_templates(self) -> List[Template]:
        """
        列出所有用户自定义模板（排除默认模板）

        Returns:
            用户模板列表
        """
        all_templates = await self.list_all()
        return [t for t in all_templates if not t.is_default]