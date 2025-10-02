"""
模板相关的API端点

提供模板的查询和创建操作
"""
import logging
import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_template_repository
from src.models.template import Template, TemplateInput
from src.storage.template_repository import TemplateRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/templates")
async def list_templates(
    template_repo: TemplateRepository = Depends(get_template_repository)
):
    """获取所有模板列表

    返回系统中所有可用的模板，包括默认模板和用户自定义模板。

    Args:
        template_repo: 模板仓库(依赖注入)

    Returns:
        模板列表，每个模板包含完整信息
    """
    templates = await template_repo.list_all()
    return [t.model_dump(mode="json") for t in templates]


@router.post("/templates", status_code=201)
async def create_template(
    template_input: TemplateInput,
    template_repo: TemplateRepository = Depends(get_template_repository),
):
    """创建自定义模板

    创建一个新的会议记录模板，可用于后续创建会议时指定。

    Args:
        template_input: 模板输入数据，包含名称和结构定义
        template_repo: 模板仓库(依赖注入)

    Returns:
        创建成功的模板完整信息

    Raises:
        HTTPException 400: 模板数据验证失败
    """
    # 创建模板对象
    template = Template(
        id=str(uuid.uuid4()),
        name=template_input.name,
        is_default=False,
        created_at=datetime.now(UTC),
        structure=template_input.structure,
    )

    # 保存到S3
    try:
        await template_repo.save(template)
    except Exception as e:
        logger.error(f"Failed to save template: {e}")
        raise HTTPException(status_code=500, detail="模板保存失败")

    return template.model_dump(mode="json")
