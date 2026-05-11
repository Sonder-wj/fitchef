# services/embedding_service.py
# 职责：文本向量化 + Milvus 向量数据库存储与检索
# 支持两种 embedding 方式：Ollama 本地模型（bge-m3）或 SentenceTransformer

from typing import Dict, List, Optional
import numpy as np
import requests
from pymilvus import (
    connections, Collection, FieldSchema, CollectionSchema, DataType,
    utility, MilvusException
)
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(service="embedding")


class EmbeddingService:
    def __init__(self):
        self.collection: Optional[Collection] = None

        self.embedding_type = settings.EMBEDDING_TYPE
        self.embedding_model_name = settings.EMBEDDING_MODEL

        if self.embedding_type == "ollama":
            self.ollama_base_url = settings.OLLAMA_BASE_URL.rstrip("/")
            self.dimension = self._detect_ollama_dimension()
            logger.info(f"使用 Ollama embedding: {self.embedding_model_name} (dim={self.dimension})")
        else:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.dimension = 384
            logger.info("使用 SentenceTransformer embedding (dim=384)")

        self._connect_milvus()

    def _connect_milvus(self):
        """连接 Milvus 并确保 collection 存在"""
        try:
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT
            )
            self._init_collection()
            self.collection.load()
            logger.info(f"Milvus 已连接，collection: {settings.MILVUS_COLLECTION}")
        except MilvusException as e:
            logger.warning(f"Milvus 连接失败，回退到无向量检索模式: {e}")
            self.collection = None

    def _init_collection(self):
        """创建或获取 Milvus collection"""
        name = settings.MILVUS_COLLECTION
        if utility.has_collection(name):
            self.collection = Collection(name)
            return

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            FieldSchema(name="doc_type", dtype=DataType.VARCHAR, max_length=32),
            FieldSchema(name="doc_name", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="text_index", dtype=DataType.INT64),
        ]
        schema = CollectionSchema(fields, description="FitChef 知识库向量索引")
        self.collection = Collection(name, schema)

        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        self.collection.create_index("embedding", index_params)
        logger.info(f"Milvus collection '{name}' 已创建，dim={self.dimension}")

    def _detect_ollama_dimension(self) -> int:
        try:
            resp = requests.post(
                f"{self.ollama_base_url}/api/embed",
                json={"model": self.embedding_model_name, "input": "test"},
                timeout=10
            )
            if resp.status_code == 200:
                return len(resp.json()["embeddings"][0])
        except Exception:
            pass
        return 1024

    def _encode(self, texts: List[str]) -> np.ndarray:
        if self.embedding_type == "ollama":
            return self._encode_ollama(texts)
        else:
            return self.model.encode(texts).astype('float32')

    def _encode_ollama(self, texts: List[str]) -> np.ndarray:
        try:
            resp = requests.post(
                f"{self.ollama_base_url}/api/embed",
                json={"model": self.embedding_model_name, "input": texts},
                timeout=60
            )
            if resp.status_code == 200:
                return np.array(resp.json()["embeddings"], dtype='float32')
            raise RuntimeError(f"Ollama embedding 失败: {resp.status_code}")
        except requests.RequestException as e:
            raise RuntimeError(f"Ollama 连接失败（{self.ollama_base_url}）: {e}")

    async def create_embeddings_from_chunks(
        self, text_chunks: list, filename: str, index_dir: str = "", user_id: int = None
    ) -> Dict:
        """批量向量化文档块并插入 Milvus"""
        if not text_chunks or not self.collection:
            return {"status": "error", "message": "无数据或 Milvus 未连接"}

        vectors = self._encode(text_chunks)
        entities = []
        for i, (text, vec) in enumerate(zip(text_chunks, vectors)):
            doc_type, doc_name = self._parse_doc_meta(text)
            entities.append({
                "content": text,
                "embedding": vec.tolist(),
                "doc_type": doc_type,
                "doc_name": doc_name,
                "source": filename,
                "text_index": i,
            })

        self.collection.insert(entities)
        self.collection.flush()
        logger.info(f"Milvus 已插入 {len(entities)} 条向量，来源: {filename}")
        return {"status": "success", "chunks": len(entities), "collection": settings.MILVUS_COLLECTION}

    def _parse_doc_meta(self, text: str) -> tuple:
        """从文档内容解析类型和名称（格式：【食材】鸡胸肉\n...）"""
        if text.startswith("【") and "】" in text[:20]:
            bracket_end = text.index("】")
            doc_type = text[1:bracket_end]
            after = text[bracket_end + 1:].strip()
            doc_name = after.split("\n")[0].strip()[:128]
            return doc_type, doc_name
        return "unknown", ""

    async def search(
        self, query: str, top_k: int = 5, doc_type: str = None
    ) -> List[Dict]:
        """向量相似度搜索，支持按文档类型过滤"""
        if not self.collection:
            return []

        query_vector = self._encode([query])

        search_params = {"metric_type": "L2", "params": {"nprobe": 16}}
        expr = f'doc_type == "{doc_type}"' if doc_type else None

        results = self.collection.search(
            data=query_vector.tolist(),
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["content", "doc_type", "doc_name", "text_index"],
        )

        output = []
        for hits in results:
            for hit in hits:
                dist = hit.distance
                score = float(1 / (1 + dist))
                output.append({
                    "content": hit.entity.get("content", ""),
                    "score": round(score, 4),
                    "doc_id": hit.entity.get("text_index", hit.id),
                    "metadata": {
                        "type": hit.entity.get("doc_type", ""),
                        "name": hit.entity.get("doc_name", ""),
                    },
                })

        return output

    def _load_index(self, index_id: str = None):
        """兼容旧接口：Milvus 中无需手动加载"""
        self.collection.load() if self.collection else None

    def clear_collection(self):
        """清空 collection（重建索引用）"""
        if self.collection:
            self.collection.release()
            utility.drop_collection(settings.MILVUS_COLLECTION)
            self._init_collection()
            self.collection.load()
            logger.info("Milvus collection 已清空重建")
