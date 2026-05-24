# services/eval_service.py
# 职责：RAG 检索质量评测
# 对比 BM25 / 向量 / 混合 / 混合+重排序 四种策略的 Hit@1/3/5 和 MRR

import asyncio
import math
import json
from pathlib import Path
from typing import List, Dict
from app.core.logger import get_logger
from app.services.hybrid_search_service import hybrid_search_service
from app.services.bm25_service import bm25_service

logger = get_logger(service="eval")

EVAL_FILE = Path(__file__).parent / "eval_questions.json"


def _load_questions() -> list:
    if EVAL_FILE.exists():
        with open(EVAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


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
        """命中判断：文档中大小写不敏感地匹配到 ≥ ceil(N/2) 个关键词"""
        text_lower = doc_text.lower()
        threshold = math.ceil(len(expect_keywords) / 2)
        matched = sum(1 for kw in expect_keywords if kw.lower() in text_lower)
        return matched >= threshold

    async def _evaluate_strategy(self, questions: list, strategy: str) -> dict:
        hits_at_1, hits_at_3, hits_at_5 = [], [], []
        reciprocal_ranks = []
        details = []

        for q in questions:
            query = q["query"]
            expect = q["expect"]

            if strategy == "bm25":
                raw = bm25_service.search(query, top_k=5)
                results = [
                    {"content": bm25_service.get_document(doc_id), "score": round(score, 4)}
                    for doc_id, score in raw
                ]
            elif strategy == "vector":
                es = _get_embedding_service()
                vec_results = await es.search(query, top_k=5)
                results = [
                    {"content": r["content"], "score": round(r["score"], 4)}
                    for r in vec_results
                ]
            elif strategy == "hybrid":
                # top_k=5：RRF 池 15×15，噪音最少，与 Hit@5 对齐
                res = await hybrid_search_service.search(query=query, top_k=5)
                results = [
                    {"content": r["content"], "score": round(r.get("rrf_score", r.get("score", 0)), 4)}
                    for r in res.get("results", [])
                ]
            else:  # hybrid+rerank
                from app.services.reranker_service import reranker_service
                # top_k=10 扩大候选池，让 reranker 能从 RRF 6-10 位捞到正确文档
                res = await hybrid_search_service.search(query=query, top_k=10)
                hybrid_results = res.get("results", [])
                rerank_res = await reranker_service.rerank(query, hybrid_results, top_k=5)
                results = [
                    {"content": r["content"], "score": round(r.get("rrf_score", r.get("score", 0)), 4)}
                    for r in rerank_res["results"]
                ]

            # 找第一个命中位置
            first_hit_rank = 0
            for rank, result in enumerate(results):
                if self._hit_at_k(result["content"], expect):
                    first_hit_rank = rank + 1
                    break

            hit_1 = first_hit_rank == 1
            hit_3 = 1 <= first_hit_rank <= 3
            hit_5 = first_hit_rank > 0
            rr = 1.0 / first_hit_rank if first_hit_rank > 0 else 0.0

            hits_at_1.append(1 if hit_1 else 0)
            hits_at_3.append(1 if hit_3 else 0)
            hits_at_5.append(1 if hit_5 else 0)
            reciprocal_ranks.append(rr)

            details.append({
                "query": query,
                "category": q.get("category", ""),
                "expect": expect,
                "hit_at_1": hit_1,
                "hit_at_3": hit_3,
                "hit_at_5": hit_5,
                "first_hit_rank": first_hit_rank if first_hit_rank > 0 else None,
                "rr": round(rr, 4),
            })

        n = len(questions)
        return {
            "strategy": strategy,
            "total_questions": n,
            "hit_at_1": sum(hits_at_1),
            "hit_at_3": sum(hits_at_3),
            "hit_at_5": sum(hits_at_5),
            "hit_rate_1": round(sum(hits_at_1) / n, 4) if n else 0,
            "hit_rate_3": round(sum(hits_at_3) / n, 4) if n else 0,
            "hit_rate_5": round(sum(hits_at_5) / n, 4) if n else 0,
            # hit_rate 保持向后兼容，等同于 hit_rate_5
            "hits": sum(hits_at_5),
            "hit_rate": round(sum(hits_at_5) / n, 4) if n else 0,
            "mrr": round(sum(reciprocal_ranks) / n, 4) if n else 0,
            "details": details,
        }

    async def run_eval(self, summary_only: bool = False) -> dict:
        """运行完整评测，对比四种检索策略"""
        self.questions = _load_questions()  # 每次评测重新读文件，避免缓存
        if not bm25_service.is_ready:
            from app.services.fitchef_loader import fitchef_loader
            texts = fitchef_loader.get_texts()
            bm25_service.build_index(texts)
            hybrid_search_service.set_documents(texts)
            es = _get_embedding_service()
            hybrid_search_service.set_embedding_service(es)

        strategies = ["bm25", "vector", "hybrid", "hybrid+rerank"]
        results = {}
        for strategy in strategies:
            results[strategy] = await self._evaluate_strategy(self.questions, strategy)

        best = max(strategies, key=lambda s: (results[s]["hit_rate_5"], results[s]["mrr"]))

        comparison = {
            s: {
                "hit_rate_1": results[s]["hit_rate_1"],
                "hit_rate_3": results[s]["hit_rate_3"],
                "hit_rate_5": results[s]["hit_rate_5"],
                "hit_rate": results[s]["hit_rate_5"],  # 向后兼容
                "mrr": results[s]["mrr"],
                "hits": results[s]["hit_at_5"],
            }
            for s in strategies
        }

        if summary_only:
            return {
                "best_strategy": best,
                "total_questions": len(self.questions),
                "comparison": comparison,
            }

        # 按类别统计（以 hybrid+rerank 为参考策略）
        cat_stats: Dict[str, Dict] = {}
        for detail in results["hybrid+rerank"]["details"]:
            cat = detail.get("category") or "未分类"
            if cat not in cat_stats:
                cat_stats[cat] = {"total": 0, "hits": 0}
            cat_stats[cat]["total"] += 1
            if detail["hit_at_5"]:
                cat_stats[cat]["hits"] += 1
        for cat, data in cat_stats.items():
            data["hit_rate"] = round(data["hits"] / data["total"], 4) if data["total"] else 0

        return {
            "strategies": results,
            "best_strategy": best,
            "comparison": comparison,
            "category_analysis": cat_stats,
        }


# 全局单例
eval_service = EvalService()
