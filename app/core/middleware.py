#请求日志中间件

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import get_logger
import time

logger = get_logger(service="http")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        # 计算处理时间
        process_time = time.time() - start_time
        
        # 记录请求日志
        # SSE 流式端点：process_time 仅为 SSE 连接建立时间，非完整处理时间
        is_sse = request.url.path in ("/chat/rag",)
        timing_note = " (SSE setup)" if is_sse else ""
        logger.info(
            f"{request.client.host}:{request.client.port} - "
            f"\"{request.method} {request.url.path} HTTP/{request.scope.get('http_version', '1.1')}\" "
            f"{response.status_code} - {process_time:.2f}s{timing_note}"
        )
        
        return response 