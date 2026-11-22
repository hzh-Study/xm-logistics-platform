"""统一错误信封与异常处理器：只注册两个处理器。"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _envelope(code: str, message: str, details=None) -> dict:
    """构造统一错误信封。"""
    return {"error": {"code": code, "message": message, "details": details}}


def register_error_handlers(app: FastAPI) -> None:
    """注册 HTTP 异常与校验异常处理器。"""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        code = exc.detail if isinstance(exc.detail, str) else "http_error"
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code, str(exc.detail), None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # 只回传字段名与消息：exc.errors() 含文件名/行号/输入原文，会泄露实现
        details = [
            {"field": ".".join(str(part) for part in err["loc"] if part != "body"), "message": err["msg"]}
            for err in exc.errors()
            if isinstance(err, dict) and "loc" in err
        ]
        return JSONResponse(
            status_code=422,
            content=_envelope("invalid_request", "请求参数不合法", details),
        )
