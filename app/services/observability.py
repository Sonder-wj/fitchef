# services/observability.py
# 职责：LangFuse LLM 可观测性 —— 追踪每次 RAG 调用的全链路耗时和输入输出

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(service="observability")

_langfuse = None


def _get_langfuse():
    global _langfuse
    if _langfuse is None:
        if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
            try:
                from langfuse import Langfuse
                _langfuse = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST,
                )
                logger.info("LangFuse 已连接")
            except Exception as e:
                logger.warning(f"LangFuse 连接失败，追踪已禁用: {e}")
                _langfuse = False
        else:
            _langfuse = False
    return _langfuse if _langfuse is not False else None


class RagTrace:
    def __init__(self, query: str):
        self._trace = None
        lf = _get_langfuse()
        if lf:
            self._trace = lf.trace(name="rag-query", input={"query": query})

    def span(self, name: str, **kwargs):
        if self._trace:
            return self._trace.span(name=name, input=kwargs.get("input"))
        return _NoopSpan()


class _NoopSpan:
    def end(self, **kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
