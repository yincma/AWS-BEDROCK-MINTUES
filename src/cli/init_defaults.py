"""
CLI工具 - 初始化默认数据

用于将默认模板初始化到S3存储桶中
"""
import asyncio
import sys
from pathlib import Path
from typing import NoReturn

# 支持直接运行脚本时添加项目根目录到Python路径
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.config import Settings
from src.models.template import DEFAULT_TEMPLATE
from src.storage.s3_client import S3ClientWrapper
from src.storage.template_repository import TemplateRepository


async def init_default_template() -> None:
    """
    初始化默认模板到S3

    检查默认模板是否已存在,如果不存在则创建。
    如果已存在,则跳过创建。

    Raises:
        Exception: S3操作失败或配置错误
    """
    settings = Settings()

    # 初始化S3客户端
    s3_client = S3ClientWrapper(
        bucket_name=settings.s3_bucket_name,
        region=settings.aws_region
    )

    # 初始化模板仓库
    template_repo = TemplateRepository(s3_client)

    # 检查默认模板是否已存在
    existing = await template_repo.get("default")

    if existing:
        print("✓ 默认模板已存在")
        print(f"  ID: {existing.id}")
        print(f"  名称: {existing.name}")
        print(f"  创建时间: {existing.created_at}")
        return

    # 保存默认模板
    await template_repo.save(DEFAULT_TEMPLATE)
    print(f"✓ 已创建默认模板: {DEFAULT_TEMPLATE.name}")
    print(f"  ID: {DEFAULT_TEMPLATE.id}")
    print(f"  章节数: {len(DEFAULT_TEMPLATE.structure.sections)}")


def show_help() -> None:
    """显示帮助信息"""
    help_text = """
AWS Bedrock Minutes - 初始化默认数据

用法:
    python -m src.cli.init_defaults [选项]
    python src/cli/init_defaults.py [选项]

选项:
    --help, -h    显示此帮助信息

描述:
    此工具将默认会议记录模板初始化到S3存储桶中。
    如果默认模板已存在,则跳过创建。

环境变量:
    AWS_REGION              AWS区域 (默认: us-east-1)
    AWS_ACCESS_KEY_ID       AWS访问密钥ID
    AWS_SECRET_ACCESS_KEY   AWS密钥
    S3_BUCKET_NAME          S3存储桶名称 (默认: meeting-minutes-dev)

示例:
    # 初始化默认模板
    python -m src.cli.init_defaults

    # 显示帮助
    python -m src.cli.init_defaults --help
"""
    print(help_text)


def main() -> NoReturn:
    """
    CLI入口函数

    解析命令行参数并执行相应操作
    """
    # 解析命令行参数
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        show_help()
        sys.exit(0)

    print("=" * 60)
    print("AWS Bedrock Minutes - 初始化默认数据")
    print("=" * 60)
    print()

    try:
        # 运行异步初始化
        asyncio.run(init_default_template())
        print()
        print("=" * 60)
        print("✓ 初始化完成")
        print("=" * 60)
        sys.exit(0)

    except KeyboardInterrupt:
        print("\n")
        print("⚠ 操作已取消")
        sys.exit(130)

    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ 错误: {str(e)}")
        print("=" * 60)
        print()
        print("请检查:")
        print("  1. AWS凭证是否正确配置")
        print("  2. S3存储桶是否存在且有访问权限")
        print("  3. 网络连接是否正常")
        print()
        print("详细错误信息:")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
