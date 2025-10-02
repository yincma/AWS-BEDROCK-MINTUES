"""
单元测试 - CLI初始化默认数据工具
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.cli.init_defaults import init_default_template
from src.models.template import DEFAULT_TEMPLATE


@pytest.mark.asyncio
async def test_init_default_template_creates_new():
    """测试创建新的默认模板"""
    # Mock S3客户端和模板仓库
    with patch('src.cli.init_defaults.S3ClientWrapper') as mock_s3, \
         patch('src.cli.init_defaults.TemplateRepository') as mock_repo_class, \
         patch('src.cli.init_defaults.Settings') as mock_settings:

        # 配置mock
        mock_settings.return_value.s3_bucket_name = "test-bucket"
        mock_settings.return_value.aws_region = "us-east-1"

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo

        # 模拟模板不存在的情况
        mock_repo.get.return_value = None
        mock_repo.save = AsyncMock()

        # 运行初始化
        await init_default_template()

        # 验证调用
        mock_repo.get.assert_called_once_with("default")
        mock_repo.save.assert_called_once_with(DEFAULT_TEMPLATE)


@pytest.mark.asyncio
async def test_init_default_template_already_exists():
    """测试默认模板已存在的情况"""
    # Mock S3客户端和模板仓库
    with patch('src.cli.init_defaults.S3ClientWrapper') as mock_s3, \
         patch('src.cli.init_defaults.TemplateRepository') as mock_repo_class, \
         patch('src.cli.init_defaults.Settings') as mock_settings:

        # 配置mock
        mock_settings.return_value.s3_bucket_name = "test-bucket"
        mock_settings.return_value.aws_region = "us-east-1"

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo

        # 模拟模板已存在
        existing_template = DEFAULT_TEMPLATE
        mock_repo.get.return_value = existing_template
        mock_repo.save = AsyncMock()

        # 运行初始化
        await init_default_template()

        # 验证调用
        mock_repo.get.assert_called_once_with("default")
        # 不应该调用save
        mock_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_init_default_template_s3_error():
    """测试S3错误情况"""
    with patch('src.cli.init_defaults.S3ClientWrapper') as mock_s3, \
         patch('src.cli.init_defaults.TemplateRepository') as mock_repo_class, \
         patch('src.cli.init_defaults.Settings') as mock_settings:

        # 配置mock
        mock_settings.return_value.s3_bucket_name = "test-bucket"
        mock_settings.return_value.aws_region = "us-east-1"

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo

        # 模拟S3错误
        mock_repo.get.side_effect = Exception("S3 connection failed")

        # 应该抛出异常
        with pytest.raises(Exception) as exc_info:
            await init_default_template()

        assert "S3 connection failed" in str(exc_info.value)


def test_default_template_structure():
    """验证默认模板结构的完整性"""
    # 验证基本属性
    assert DEFAULT_TEMPLATE.id == "default"
    assert DEFAULT_TEMPLATE.name == "标准会议记录模板"
    assert DEFAULT_TEMPLATE.is_default is True
    assert DEFAULT_TEMPLATE.creator_identifier is None

    # 验证结构
    assert len(DEFAULT_TEMPLATE.structure.sections) == 2

    # 验证第一个章节
    section1 = DEFAULT_TEMPLATE.structure.sections[0]
    assert section1.name == "会议基本信息"
    assert len(section1.fields) == 3

    # 验证字段
    field_keys = [f.key for f in section1.fields]
    assert "title" in field_keys
    assert "date" in field_keys
    assert "participants" in field_keys

    # 验证第二个章节
    section2 = DEFAULT_TEMPLATE.structure.sections[1]
    assert section2.name == "会议内容"
    assert len(section2.fields) == 3

    # 验证字段
    field_keys2 = [f.key for f in section2.fields]
    assert "topics" in field_keys2
    assert "decisions" in field_keys2
    assert "action_items" in field_keys2
