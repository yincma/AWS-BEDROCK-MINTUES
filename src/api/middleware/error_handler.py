"""
错误处理中间件

提供统一的异常处理和错误响应格式，包括:
- 全局异常捕获
- Pydantic验证错误处理
- 标准化错误响应格式
"""
import logging
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)


async def error_handler_middleware(request: Request, call_next) -> JSONResponse:
    """全局错误处理中间件

    捕获所有未处理的异常，返回统一格式的错误响应。

    Args:
        request: FastAPI请求对象
        call_next: 下一个中间件或路由处理器

    Returns:
        JSONResponse: 正常响应或错误响应
    """
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        # 记录异常堆栈
        logger.exception(
            "Unhandled exception occurred",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client": request.client.host if request.client else None,
                "error_type": type(exc).__name__,
            },
        )

        # 返回统一格式的错误响应
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "服务器内部错误，请稍后重试",
                "details": {},
            },
        )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Pydantic验证错误处理器

    处理请求参数验证失败的情况，返回详细的验证错误信息。

    Args:
        request: FastAPI请求对象
        exc: 验证错误异常

    Returns:
        JSONResponse: 格式化的验证错误响应
    """
    # 序列化错误信息，避免不可序列化对象
    errors = []
    for error in exc.errors():
        error_dict = {
            "type": error.get("type"),
            "loc": list(error.get("loc", [])),
            "msg": str(error.get("msg", "")),
        }
        # 安全地转换 input/ctx 为字符串
        if "input" in error:
            try:
                error_dict["input"] = str(error["input"])[:200]
            except Exception:
                error_dict["input"] = "<unable to serialize>"
        if "ctx" in error:
            try:
                error_dict["ctx"] = {k: str(v) for k, v in error["ctx"].items()}
            except Exception:
                error_dict["ctx"] = {}
        errors.append(error_dict)

    # 记录验证错误
    logger.warning(
        "Request validation failed",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": errors,
        },
    )

    # 返回详细的验证错误信息
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "请求参数验证失败",
            "details": errors,
        },
    )


async def pydantic_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Pydantic模型验证错误处理器

    处理内部数据模型验证失败的情况。

    Args:
        request: FastAPI请求对象
        exc: Pydantic验证错误

    Returns:
        JSONResponse: 格式化的验证错误响应
    """
    # 序列化错误信息，避免datetime等不可序列化对象
    errors = []
    for error in exc.errors():
        error_dict = {
            "type": error.get("type"),
            "loc": list(error.get("loc", [])),
            "msg": str(error.get("msg", "")),
        }
        # 安全地转换input为字符串
        if "input" in error:
            try:
                error_dict["input"] = str(error["input"])[:200]  # 限制长度
            except Exception:
                error_dict["input"] = "<unable to serialize>"
        errors.append(error_dict)

    logger.error(
        "Pydantic model validation failed",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": errors,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "model_validation_error",
            "message": "数据模型验证失败",
            "details": errors,
        },
    )
