# services/reranker_service.py
# 职责：对检索结果重排序（Cross-Encoder），提升 Top-3 精准度
# 使用 sentence-transformers 的 Cross-Encoder 模型
# 如果模型加载失败，降级为保留原始排序

from typing import List, Dict, Optional
import asyncio
from app.core.logger import get_logger

logger = get_logger(service="reranker")

# 延迟加载模型
_reranker_model = None


def _get_model():
    global _reranker_model
    if _reranker_model is None:
        try:
            from sentence_transformers import CrossEncoder
            import os

            model_name = "BAAI/bge-reranker-v2-m3"
            # 优先检查挂载路径（Docker volume 直接挂载的模型）
            mount_path = "/app/models/reranker"
            if os.path.isfile(os.path.join(mount_path, "model.safetensors")):
                model_path = mount_path
            else:
                # 从 ModelScope 下载（国内可用，国外也能用）
                logger.info(f"重排序模型未找到，从 ModelScope 下载 {model_name}...")
                from modelscope import snapshot_download
                model_path = snapshot_download(model_name)
                logger.info(f"重排序模型下载完成: {model_path}")

            logger.info(f"加载重排序模型: {model_path}")
            _reranker_model = CrossEncoder(model_path)
            logger.info("Cross-Encoder 模型加载成功")
        except Exception as e:
            logger.warning(f"Cross-Encoder 模型加载失败，将使用原始排序: {e}")
            _reranker_model = False
    return _reranker_model if _reranker_model is not False else None


class RerankerService:
    """搜索结果重排序服务"""

    def __init__(self):
        self.model = None

    async def _load_model(self):
        if self.model is None:
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(None, _get_model)

    async def rerank(self, query: str, results: List[Dict], top_k: int = 5) -> Dict:
        """
        对检索结果用 Cross-Encoder 重排序
        如果模型未就绪，快速跳过（不阻塞）
        """
        before = [{"content": r["content"][:200], "score": r.get("rrf_score", r.get("score", 0))} for r in results]

        if not results or len(results) < 2:
            return {"results": results, "before": before, "after": before, "reranked": False}

        # 模型加载失败过，不再重试
        if _reranker_model is False:
            return {"results": results, "before": before, "after": before, "reranked": False}

        # 首次调用时加载模型
        await self._load_model()

        if self.model is None:
            # 模型不可用，保留原序
            return {"results": results, "before": before, "after": before, "reranked": False}

        try:
            # 构建 (query, document) 对
            pairs = [(query, results[i]["content"][:500]) for i in range(len(results))]

            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(None, self.model.predict, pairs)

            # 重排序
            indexed = [(i, float(scores[i])) for i in range(len(scores))]
            indexed.sort(key=lambda x: x[1], reverse=True)

            reranked = [results[i] for i, _ in indexed[:top_k]]
            after = [{**reranked[j], "rerank_score": round(float(scores[i]), 4)}
                     for j, (i, _) in enumerate(indexed[:top_k])]

            logger.info(f"重排序完成，Top-3 分数: {[round(scores[i], 4) for i, _ in indexed[:3]]}")
            return {
                "results": reranked,
                "before": before,
                "after": after,
                "reranked": True,
            }

        except Exception as e:
            logger.warning(f"重排序出错: {e}")
            return {"results": results, "before": before, "after": before, "reranked": False}


# 全局单例
reranker_service = RerankerService()
