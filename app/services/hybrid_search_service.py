# services/hybrid_search_service.py
# 职责：融合 BM25 关键词检索 + FAISS 向量检索，用 RRF 算法
# 返回统一格式的检索结果

import asyncio
from typing import List, Dict, Optional
from app.core.logger import get_logger
from app.services.bm25_service import bm25_service

logger = get_logger(service="hybrid_search")


class HybridSearchService:
    """混合检索：BM25 + FAISS 向量 → RRF 融合"""

    def __init__(self):
        self.bm25 = bm25_service
        self.embedding_service = None  # 延迟注入
        self.doc_texts: List[str] = []

    def set_embedding_service(self, service):
        self.embedding_service = service

    def set_documents(self, documents: List[str]):
        self.doc_texts = documents
        self.bm25.build_index(documents)

    def _rrf_fusion(self, bm25_results: List[tuple], vector_results: List[tuple],
                    k: int = 10, top_k: int = 5, min_score: float = 0.01,
                    bm25_weight: float = 0.15, vector_weight: float = 0.85) -> List[Dict]:
        """
        RRF (Reciprocal Rank Fusion) 融合算法
        公式：RRF(d) = Σ w_i / (k + rank_i(d))
        k: 平滑参数（论文默认 60，经实验 3~60 对本数据集结果无影响，保持 10）
        bm25_weight / vector_weight: 评测最优 0.3/0.7，Hit@5 与 MRR 均衡最佳
        """
        scores = {}

        # BM25 结果
        for rank, (doc_id, bm25_score) in enumerate(bm25_results):
            scores[doc_id] = scores.get(doc_id, 0) + bm25_weight / (k + rank + 1)

        # 向量检索结果
        for rank, (doc_id, vector_score) in enumerate(vector_results):
            scores[doc_id] = scores.get(doc_id, 0) + vector_weight / (k + rank + 1)

        # 排序
        sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results = []
        for doc_id, rrf_score in sorted_ids[:top_k]:
            if doc_id < len(self.doc_texts):
                results.append({
                    "content": self.doc_texts[doc_id],
                    "rrf_score": round(rrf_score, 4),
                    "doc_id": doc_id,
                })

        return results

    async def search(self, query: str = "", top_k: int = 5,
                     bm25_query: str = None, vector_query: str = None,
                     bm25_weight: float = 0.3, vector_weight: float = 0.7,
                     rrf_k: int = 10) -> Dict:
        """
        执行混合检索，返回结构化结果
        bm25_query: 用于 BM25 关键词检索（默认取 query）
        vector_query: 用于向量语义检索（默认取 query）
        bm25_weight / vector_weight: RRF 融合权重（默认 0.3 / 0.7）
        """
        if not self.doc_texts:
            return {"query": query, "results": [], "method": "hybrid", "total": 0}

        bm25_q = bm25_query or query
        vec_q = vector_query or query

        loop = asyncio.get_event_loop()

        bm25_future = loop.run_in_executor(None, self.bm25.search, bm25_q, top_k * 3)
        vector_results = []

        if self.embedding_service:
            try:
                vector_results_raw = await self.embedding_service.search(vec_q, top_k * 3)
                for v in vector_results_raw:
                    doc_id = v.get("doc_id", -1)
                    if doc_id >= 0 and doc_id < len(self.doc_texts):
                        vector_results.append((doc_id, v.get("score", 0)))
            except Exception as e:
                logger.warning(f"向量检索失败，回退至纯 BM25: {e}")

        bm25_raw = await bm25_future

        # RRF 融合
        merged = self._rrf_fusion(bm25_raw, vector_results, k=rrf_k, top_k=top_k,
                                  bm25_weight=bm25_weight, vector_weight=vector_weight)

        # 分别获取 BM25-only 和 Vector-only 的结果用于对比
        bm25_only = []
        for doc_id, score in bm25_raw[:top_k]:
            if doc_id < len(self.doc_texts):
                bm25_only.append({
                    "content": self.doc_texts[doc_id],
                    "score": round(score, 4),
                    "doc_id": doc_id,
                })

        vector_only = []
        for doc_id, score in vector_results[:top_k]:
            if doc_id < len(self.doc_texts):
                vector_only.append({
                    "content": self.doc_texts[doc_id],
                    "score": round(score, 4),
                    "doc_id": doc_id,
                })

        return {
            "query": query,
            "bm25_query": bm25_q,
            "vector_query": vec_q,
            "results": merged,
            "bm25_results": bm25_only,
            "vector_results": vector_only,
            "method": "hybrid_rrf",
            "total": len(merged),
        }


# 全局单例
hybrid_search_service = HybridSearchService()
