"""
AWS Bedrock Minutes API 主应用入口

提供完整的FastAPI应用配置，包括:
- 路由注册
- CORS中间件
- 错误处理中间件
- 日志中间件
- 应用生命周期管理
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from src.api.middleware import (
    error_handler_middleware,
    logging_middleware,
    validation_exception_handler,
)
from src.api.middleware.error_handler import pydantic_exception_handler
from src.api.middleware.logger import configure_json_logging, configure_standard_logging
from src.config import get_settings
from src.storage.s3_client import S3ClientWrapper
from src.storage.template_repository import TemplateRepository

# 配置日志格式 (根据环境变量)
log_level = os.getenv("LOG_LEVEL", "INFO")
log_format = os.getenv("LOG_FORMAT", "standard")  # standard or json

if log_format.lower() == "json":
    configure_json_logging(log_level)
else:
    configure_standard_logging(log_level)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理

    启动时:
    - 初始化S3客户端
    - 创建默认模板(如果不存在)

    关闭时:
    - 清理资源
    """
    logger.info("Starting AWS Bedrock Minutes API...")

    # 初始化默认模板
    settings = get_settings()
    s3_client = S3ClientWrapper(
        bucket_name=settings.s3_bucket_name, region=settings.aws_region
    )
    template_repo = TemplateRepository(s3_client)
    await template_repo._ensure_default_template()

    logger.info("Application startup complete")

    yield

    logger.info("Shutting down application...")


app = FastAPI(
    title="AWS Bedrock Minutes API",
    version="1.0.0",
    description="三阶段会议记录生成系统 (制作-审查-优化)",
    lifespan=lifespan,
)

# ========================================
# 中间件注册 (按照从外到内的顺序)
# ========================================

# 1. CORS中间件 (最外层)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 日志中间件
app.middleware("http")(logging_middleware)

# 3. 错误处理中间件
app.middleware("http")(error_handler_middleware)

# 4. 异常处理器注册
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ValidationError, pydantic_exception_handler)

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


# 注册路由
from src.api.routes import meetings, templates

app.include_router(meetings.router, prefix="/api/v1", tags=["meetings"])
app.include_router(templates.router, prefix="/api/v1", tags=["templates"])
