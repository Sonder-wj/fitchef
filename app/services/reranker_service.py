# services/reranker_service.py
# 职责：调用 reranker Docker 微服务进行 Cross-Encoder 重排序
# 微服务地址由 RERANKER_URL 环境变量控制，默认 http://localhost:8001

import os
import asyncio
from typing import List, Dict
import httpx
from app.core.logger import get_logger

logger = get_logger(service="reranker")

RERANKER_URL = os.getenv("RERANKER_URL", "http://localhost:8001")


class RerankerService:
    """通过 HTTP 调用 reranker 微服务，失败时静默降级为原序"""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=RERANKER_URL, timeout=30.0)
        return self._client

    async def rerank(self, query: str, results: List[Dict], top_k: int = 5) -> Dict:
        """
        重排序入口。
        如果微服务不可达或返回错误，静默保留原排序（reranked=False）。
        """
        before = [
            {"content": r["content"][:200], "score": r.get("rrf_score", r.get("score", 0))}
            for r in results
        ]

        if not results or len(results) < 2:
            return {"results": results, "before": before, "after": before, "reranked": False}

        try:
            client = await self._get_client()
            documents = [r["content"][:500] for r in results]
            resp = await client.post("/rerank", json={"query": query, "documents": documents})
            resp.raise_for_status()
            data = resp.json()

            scores = data["scores"]
            ranked_indices = data["ranked_indices"][:top_k]

            reranked = [results[i] for i in ranked_indices]
            after = [
                {**results[i], "rerank_score": round(scores[i], 4)}
                for i in ranked_indices
            ]

            logger.info(f"重排序完成，Top-3 分数: {[round(scores[i], 4) for i in ranked_indices[:3]]}")
            return {"results": reranked, "before": before, "after": after, "reranked": True}

        except Exception as e:
            logger.warning(f"reranker 服务不可达，保留原序: {e}")
            return {"results": results, "before": before, "after": before, "reranked": False}


# 全局单例
reranker_service = RerankerService()
