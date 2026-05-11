# services/bm25_service.py
# 职责：BM25 关键词检索，对中文分词后建索引，支持查询
# 与 FAISS 向量检索互补——关键词匹配 + 语义匹配

import jieba
from typing import List, Tuple
from rank_bm25 import BM25Okapi
from app.core.logger import get_logger

logger = get_logger(service="bm25")


class BM25Service:
    """BM25 关键词检索服务"""

    def __init__(self):
        self.index: BM25Okapi = None
        self.documents: List[str] = []
        self.tokenized_docs: List[List[str]] = []
        self.is_ready = False

    def build_index(self, documents: List[str]):
        """分词 → 建 BM25 索引"""
        self.documents = documents
        self.tokenized_docs = [list(jieba.cut(doc)) for doc in documents]
        self.index = BM25Okapi(self.tokenized_docs)
        self.is_ready = True
        logger.info(f"BM25 索引构建完成，共 {len(documents)} 条文档")

    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        """
        搜索并返回 (doc_index, score) 列表
        score 已归一化到 0-1 范围（近似）
        """
        if not self.is_ready:
            logger.warning("BM25 索引未就绪")
            return []

        tokenized_query = list(jieba.cut(query))
        scores = self.index.get_scores(tokenized_query)

        # 归一化分数（除以理论最大值）
        max_score = max(scores) if max(scores) > 0 else 1.0
        indexed = [(i, scores[i] / max_score) for i in range(len(scores)) if scores[i] > 0]
        indexed.sort(key=lambda x: x[1], reverse=True)

        return indexed[:top_k]

    def get_document(self, idx: int) -> str:
        if 0 <= idx < len(self.documents):
            return self.documents[idx]
        return ""


# 全局单例
bm25_service = BM25Service()
