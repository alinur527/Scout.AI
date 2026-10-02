from starlette.responses import JSONResponse
from starlette.formparsers import MultiPartException


class BodyLimitMiddleware:
    """Bound uploads before multipart parsing fills temporary storage, including chunked requests."""

    def __init__(self, app, max_bytes):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH"):
            return await self.app(scope, receive, send)
        limit = self.max_bytes if scope["path"] == "/analyses" else 65536
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = limit + 1
        if declared > limit:
            return await JSONResponse({"detail": "Request body exceeds the configured size limit"}, 413)(
                scope, receive, send
            )
        total = 0
        exceeded = False

        async def limited_receive():
            nonlocal total, exceeded
            message = await receive()
            total += len(message.get("body", b""))
            if total > limit:
                exceeded = True
                # Starlette closes partial multipart temporary files for this exception.
                raise MultiPartException("Request body limit exceeded")
            return message

        async def guarded_send(message):
            if not exceeded:
                await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            if not exceeded:
                raise
        finally:
            if exceeded:
                await JSONResponse({"detail": "Request body exceeds the configured size limit"}, 413)(
                    scope, receive, send
                )
