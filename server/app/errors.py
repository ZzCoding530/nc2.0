"""统一错误结构（03 文档 §1）：
HTTP 状态码 + {"error": {"code": ..., "message": ...}}
"""
from fastapi import Request
from fastapi.responses import JSONResponse

ERROR_MESSAGES = {
    "INVALID_CREDENTIALS": (401, "邮箱或密码错误"),
    "ACCOUNT_PENDING": (403, "账号尚未激活，请先查收验证邮件"),
    "ACCOUNT_LOCKED": (429, "失败次数过多，账号已锁定 10 分钟，请查收邮件"),
    "EMAIL_NOT_WHITELISTED": (403, "该邮箱未在开班名单中，请联系班主任"),
    "EMAIL_TAKEN": (409, "该邮箱已注册，请直接登录"),
    "TOKEN_INVALID": (400, "链接无效或已被使用"),
    "TOKEN_EXPIRED": (400, "链接已过期，请重新获取"),
    "NOT_FOUND": (404, "资源不存在"),
    "LESSON_LOCKED": (403, "预习尚未解锁"),
    "SCHEDULE_CONFLICT": (409, "该课时已存在排期"),
    "LINK_REQUIRED": (400, "上课链接为空，请先填写后再发送"),
    "FORBIDDEN": (403, "无权访问"),
    "VALIDATION_ERROR": (400, "参数不合法"),
    "UNAUTHORIZED": (401, "请先登录"),
    "RATE_LIMITED": (429, "操作过于频繁，请稍后再试"),
}


class AppError(Exception):
    def __init__(self, code: str, message: str | None = None, http_status: int | None = None):
        self.code = code
        default_status, default_msg = ERROR_MESSAGES.get(code, (400, "请求失败"))
        self.http_status = http_status or default_status
        self.message = message or default_msg
        super().__init__(self.message)


def register_error_handler(app) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(_req: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
