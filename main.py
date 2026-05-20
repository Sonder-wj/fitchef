# main.py
# 职责：FastAPI 应用入口
#   1. 创建 app 实例
#   2. 注册中间件（日志、CORS）
#   3. 注册所有路由
#   4. 启动时自动建表

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import json
from app.core.database import engine, Base
from app.core.logger import get_logger
from app.routers import auth, chat
from pathlib import Path
from app.core.middleware import LoggingMiddleware

logger = get_logger(service="main")

# 项目根目录
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
FRONTEND_DIR = BASE_DIR / "frontend"

UPLOAD_DIR.mkdir(exist_ok=True)
FRONTEND_DIR.mkdir(exist_ok=True)

# ── 启动/关闭事件 ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        from app.models.user import User
        from app.models.conversation import Conversation
        from app.models.message import Message
        from app.models.workout import Workout, WorkoutExercise, WorkoutSet
        from app.models.body_metric import BodyMetric
        from app.models.diet import DietMeal, DietFoodItem
        from app.models.user_goal import UserGoal
        await conn.run_sync(Base.metadata.create_all)
        # 旧表补充 summary 列
        try:
            from sqlalchemy import text
            await conn.execute(text("ALTER TABLE conversations ADD COLUMN summary TEXT"))
        except Exception:
            pass  # 列已存在则跳过
    logger.info("数据库表初始化完成")

    # 加载 Embedding 模型 + 初始化 RAG 知识库（含 FAISS 向量索引）
    import asyncio
    from app.services.embedding_service import EmbeddingService

    try:
        loop = asyncio.get_running_loop()
        svc = await loop.run_in_executor(None, EmbeddingService)
        app.state.embedding_service = svc
        logger.info("Embedding 模型加载成功")

        # 初始化 RAG（BM25 + Milvus 向量索引）
        from app.services.rag_chat_service import rag_chat_service
        from app.services.fitchef_loader import fitchef_loader

        docs = fitchef_loader.load()
        texts = fitchef_loader.get_texts()
        logger.info(f"FitChef 知识库加载: {fitchef_loader.get_stats()}")

        # BM25 索引（同步，快速）
        from app.services.hybrid_search_service import hybrid_search_service
        hybrid_search_service.set_documents(texts)
        hybrid_search_service.set_embedding_service(svc)

        # Milvus 向量索引（自动持久化，增量更新）
        import time as _time
        t0 = _time.time()
        from pymilvus import utility
        if svc.collection and svc.collection.num_entities == 0:
            await svc.create_embeddings_from_chunks(texts, filename="fitchef_knowledge")
            logger.info(f"Milvus 向量索引构建完成，{len(texts)} 条，耗时 {_time.time()-t0:.1f}s")
        else:
            logger.info(f"Milvus 向量索引已存在，跳过构建，耗时 {_time.time()-t0:.1f}s")

        rag_chat_service.is_ready = True
        logger.info("FitChef RAG 知识库初始化完成")

        # 后台预加载重排序模型（不阻塞启动）
        # 重排序模型预加载暂时禁用（Windows 页文件不足导致 segfault）
        # async def preload_reranker():
        #     try:
        #         from app.services.reranker_service import _get_model
        #         await loop.run_in_executor(None, _get_model)
        #         logger.info("重排序模型预加载完成")
        #     except Exception as e:
        #         logger.warning(f"重排序模型预加载失败（将跳过重排序）: {e}")
        # asyncio.create_task(preload_reranker())

        # 后台预加载查询改写模型（预热 DeepSeek API 连接）
        async def preload_rewriter():
            try:
                from app.services.query_rewriter_service import query_rewriter_service
                await query_rewriter_service.rewrite("test")
                logger.info("查询改写服务预热完成")
            except Exception:
                pass
        asyncio.create_task(preload_rewriter())

    except Exception as e:
        import traceback
        logger.warning(f"初始化失败（RAG 功能将回退至纯 BM25）: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        app.state.embedding_service = None
        from app.services.rag_chat_service import rag_chat_service
        from app.services.fitchef_loader import fitchef_loader
        from app.services.hybrid_search_service import hybrid_search_service
        try:
            fitchef_loader.load()
            hybrid_search_service.set_documents(fitchef_loader.get_texts())
            rag_chat_service.is_ready = True
            logger.info("RAG 已回退至 BM25-only 模式")
        except Exception as e2:
            logger.error(f"RAG 初始化完全失败: {type(e2).__name__}: {e2}\n{traceback.format_exc()}")

    yield
    await engine.dispose()
    logger.info("数据库连接已关闭")

# ── 创建 FastAPI 实例 ─────────────────────────────────────────
app = FastAPI(
    title="FitChef — 健身餐营养助手",
    description="基于混合检索与 AI 生成的智能饮食知识平台",
    version="2.0.0",
    lifespan=lifespan
)

# ── 中间件 ────────────────────────────────────────────────────
# 注意：中间件按注册顺序倒序执行（后注册的先执行）

app.add_middleware(LoggingMiddleware)  # 记录每个请求的耗时和状态码
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 路由注册 ──────────────────────────────────────────────────
app.include_router(auth.router) # /auth/register、/auth/login、/auth/me
app.include_router(chat.router)  # /chat/send、/chat/conversations、/chat/agent 等


# ── 健康检查 ──────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}

# ── 前端页面 ──────────────────────────────────────────────────
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR), html=False), name="uploads")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
