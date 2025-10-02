"""
简化的Template模型定义 - 用于AI服务测试
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class Field(BaseModel):
    """模板字段"""
    name: str
    description: str
    required: bool = False


class Section(BaseModel):
    """模板章节"""
    name: str
    level: int = 2
    fields: List[Field]


class Template(BaseModel):
    """会议记录模板"""
    name: str
    description: str
    category: str
    sections: List[Section]
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime