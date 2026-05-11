# services/eval_service.py
# 职责：RAG 检索质量评测
# 对比 BM25 / 向量 / 混合检索 三种策略的 Hit Rate 和 MRR

import asyncio
import time
import json
from pathlib import Path
from typing import List, Dict
from app.core.logger import get_logger
from app.services.hybrid_search_service import hybrid_search_service
from app.services.bm25_service import bm25_service

logger = get_logger(service="eval")

# 从 JSON 文件加载评测集
EVAL_FILE = Path(__file__).parent / "eval_questions.json"

def _load_questions() -> list:
    if EVAL_FILE.exists():
        with open(EVAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 延迟复用 EmbeddingService，避免每次评测都调 Ollama 测维度
_embedding_service = None

def _get_embedding_service():
    global _embedding_service
    if _embedding_service is None:
        from app.services.embedding_service import EmbeddingService
        _embedding_service = EmbeddingService()
        _embedding_service._load_index("fitchef_knowledge")
    return _embedding_service


class EvalService:
    """检索质量评测服务"""

    def __init__(self):
        self.questions = _load_questions()

    def _hit_at_k(self, doc_text: str, expect_keywords: list) -> bool:
        """检查文档是否命中预期关键词"""
        for kw in expect_keywords:
            if kw in doc_text:
                return True
        return False

    async def _evaluate_strategy(self, questions: list, strategy: str) -> dict:
        """
        评测一种检索策略
        strategy: "bm25" | "vector" | "hybrid"
        """
        hits = []
        reciprocal_ranks = []
        details = []

        for q in questions:
            query = q["query"]
            expect = q["expect"]

            if strategy == "bm25":
                raw = bm25_service.search(query, top_k=5)
                results = [{"content": bm25_service.get_document(doc_id), "score": round(score, 4)}
                            for doc_id, score in raw]
            elif strategy == "vector":
                es = _get_embedding_service()
                vec_results = await es.search(query, top_k=5)
                results = [{"content": r["content"], "score": round(r["score"], 4)}
                            for r in vec_results]
            else:  # hybrid
                hybrid_result = await hybrid_search_service.search(query=query, top_k=5)
                results = [{"content": r["content"], "score": round(r.get("rrf_score", r.get("score", 0)), 4)}
                            for r in hybrid_result.get("results", [])]

            hit = False
            first_hit_rank = 0
            for rank, result in enumerate(results):
                if self._hit_at_k(result["content"], expect):
                    hit = True
                    if first_hit_rank == 0:
                        first_hit_rank = rank + 1
                    break

            hits.append(1 if hit else 0)
            rr = 1.0 / first_hit_rank if first_hit_rank > 0 else 0
            reciprocal_ranks.append(rr)

            details.append({
                "query": query,
                "expect": expect,
                "hit": hit,
                "first_hit_rank": first_hit_rank if first_hit_rank > 0 else None,
                "rr": round(rr, 4),
            })

        hit_rate = round(sum(hits) / len(hits), 4) if hits else 0
        mrr = round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4) if reciprocal_ranks else 0

        return {
            "strategy": strategy,
            "total_questions": len(questions),
            "hits": sum(hits),
            "hit_rate": hit_rate,
            "mrr": mrr,
            "details": details,
        }

    async def run_eval(self) -> dict:
        """运行完整评测，对比三种策略"""
        if not bm25_service.is_ready:
            from app.services.fitchef_loader import fitchef_loader
            texts = fitchef_loader.get_texts()
            bm25_service.build_index(texts)
            hybrid_search_service.set_documents(texts)
            es = _get_embedding_service()
            hybrid_search_service.set_embedding_service(es)

        strategies = ["bm25", "vector", "hybrid"]
        results = {}
        for strategy in strategies:
            results[strategy] = await self._evaluate_strategy(self.questions, strategy)

        best = max(strategies, key=lambda s: results[s]["hit_rate"])

        return {
            "strategies": results,
            "best_strategy": best,
            "comparison": {
                s: {
                    "hit_rate": results[s]["hit_rate"],
                    "mrr": results[s]["mrr"],
                    "hits": results[s]["hits"],
                }
                for s in strategies
            },
        }


# 全局单例
eval_service = EvalService()
