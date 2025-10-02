"""
日志中间件

提供请求/响应日志记录功能，包括:
- 结构化JSON日志
- 请求/响应时间统计
- 处理时间Header
- 可配置的日志级别
"""
import json
import logging
import sys
import time
import uuid
from typing import Callable

from fastapi import Request, Response

logger = logging.getLogger(__name__)


class JSONFormatter(logging.Formatter):
    """JSON格式日志formatter

    用于生产环境的结构化日志输出，便于CloudWatch等日志系统解析。
    """

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON字符串

        Args:
            record: 日志记录对象

        Returns:
            JSON格式的日志字符串
        """
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加额外的上下文信息
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def configure_json_logging(log_level: str = "INFO") -> None:
    """配置JSON格式日志

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # 清除现有handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 配置JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))


def configure_standard_logging(log_level: str = "INFO") -> None:
    """配置标准格式日志 (开发环境)

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """请求/响应日志中间件

    记录每个请求的详细信息和处理时间。

    Args:
        request: FastAPI请求对象
        call_next: 下一个中间件或路由处理器

    Returns:
        Response: 添加了处理时间Header的响应对象
    """
    # 生成请求ID (用于追踪)
    request_id = str(uuid.uuid4())

    # 记录请求开始
    start_time = time.time()

    # 提取请求信息
    client_host = request.client.host if request.client else "unknown"
    client_port = request.client.port if request.client else 0

    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_host": client_host,
            "client_port": client_port,
            "user_agent": request.headers.get("user-agent", ""),
        },
    )

    # 处理请求
    response = await call_next(request)

    # 计算处理时间
    process_time = time.time() - start_time

    # 记录响应
    logger.info(
        f"Request completed: {response.status_code} ({process_time:.3f}s)",
        extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "process_time": process_time,
            "method": request.method,
            "path": request.url.path,
        },
    )

    # 添加处理时间和请求ID到响应Header
    response.headers["X-Process-Time"] = f"{process_time:.3f}"
    response.headers["X-Request-ID"] = request_id

    return response


async def request_body_logging_middleware(
    request: Request, call_next: Callable
) -> Response:
    """请求体日志中间件 (仅用于开发环境)

    记录请求和响应的完整内容，仅用于调试。
    注意: 不应在生产环境使用，可能暴露敏感信息。

    Args:
        request: FastAPI请求对象
        call_next: 下一个中间件或路由处理器

    Returns:
        Response: 响应对象
    """
    # 读取请求体
    body = await request.body()

    logger.debug(
        "Request body",
        extra={
            "path": request.url.path,
            "method": request.method,
            "body": body.decode("utf-8") if body else "",
        },
    )

    # 处理请求
    response = await call_next(request)

    return response
