# routers/chat.py
# 职责：RAG 知识库问答、评测、知识库管理

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import json
import asyncio
from app.core.database import get_db, AsyncSessionLocal
from app.core.logger import get_logger
from app.core.security import get_current_user
from app.models.user import User
from app.models.conversation import DialogueType
from app.services.conversation_service import ConversationService
from app.services.rag_chat_service import rag_chat_service, _safe_background

from app.services.eval_service import eval_service
from app.services.hybrid_search_service import hybrid_search_service

logger = get_logger(service="chat_router")
router = APIRouter(prefix="/chat", tags=["对话"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    dialogue_type: str = "RAG 问答"


# ═══════════════════════════════════════════════════════════════
# 会话管理
# ═══════════════════════════════════════════════════════════════

@router.get("/conversations", summary="获取会话列表")
async def list_conversations(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.conversation_service import ConversationService
    return await ConversationService.get_conversations(db, current_user.id)


@router.post("/conversations", summary="创建新会话")
async def create_conversation(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.conversation_service import ConversationService
    from app.models.conversation import DialogueType
    conv = await ConversationService.create_conversation(db, current_user.id, DialogueType.RAG)
    return {"id": conv.id, "title": conv.title, "created_at": str(conv.created_at)}


@router.get("/conversations/{conv_id}/messages", summary="获取会话消息")
async def get_messages(conv_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.conversation_service import ConversationService
    return await ConversationService.get_messages(db, conv_id)


@router.delete("/conversations/{conv_id}", summary="删除会话")
async def delete_conversation(conv_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.conversation_service import ConversationService
    await ConversationService.delete_conversation(db, conv_id, current_user.id)
    return {"message": "已删除"}


# ═══════════════════════════════════════════════════════════════
# RAG 知识库问答
# ═══════════════════════════════════════════════════════════════

@router.post("/rag", summary="FitChef 营养知识库问答（流式）")
async def rag_endpoint(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """RAG 知识库问答 + 会话持久化"""
    import traceback as _traceback
    from app.services.conversation_service import ConversationService
    from app.models.conversation import DialogueType

    try:
        # 创建或复用会话
        if not req.conversation_id:
            conv = await ConversationService.create_conversation(db, current_user.id, DialogueType.RAG)
            conv_id = conv.id
        else:
            conv_id = req.conversation_id
            # 获取会话（需要 summary）
            from sqlalchemy import select
            from app.models.conversation import Conversation
            r = await db.execute(select(Conversation).where(Conversation.id == conv_id))
            conv = r.scalar_one_or_none()

        # 加载历史消息（最近 10 条）+ 摘要 + 偏好
        history = await ConversationService.get_messages(db, conv_id, limit=10)
        conv_summary = conv.summary if conv and conv.summary else ""
        conv_preferences = conv.user_preferences if conv and conv.user_preferences else {}

        async def stream_with_images():
            nonlocal conv_summary
            full_answer = ""
            try:
                hist = [{"role": m.sender, "content": m.content} for m in history]

                async for chunk in rag_chat_service.generate_stream(
                    req.message, user_id=current_user.id, history=hist, summary=conv_summary, user_preferences=conv_preferences
                ):
                    yield chunk
                    if chunk.startswith("data: "):
                        try:
                            d = json.loads(chunk[6:].strip())
                            if isinstance(d, str):
                                full_answer += d
                        except (json.JSONDecodeError, KeyError):
                            pass

                # 保存消息到 MySQL
                if full_answer:
                    try:
                        await ConversationService.save_message(db, conv_id, req.message, full_answer)
                        await db.commit()

                        # 摘要更新策略：每 3 轮 / 首轮 / token 超阈值时触发
                        exchange_count = len(hist) // 2 + 1
                        recent_chars = sum(len(m["content"]) for m in hist[-6:])
                        recent_chars += len(req.message) + len(full_answer)
                        token_estimate = recent_chars // 2  # 中文约 2 字符/token
                        token_overflow = token_estimate > 2000

                        if exchange_count % 3 == 0 or exchange_count == 1 or token_overflow:
                            recent_exchanges = []
                            for m in hist[-6:]:
                                role = "用户" if m["role"] == "user" else "AI"
                                recent_exchanges.append(f"{role}: {m['content'][:100]}")
                            recent_exchanges.append(f"用户: {req.message}")
                            recent_exchanges.append(f"AI: {full_answer[:300]}")
                            new_exchange = "\n".join(recent_exchanges)
                            _safe_background(
                                ConversationService.update_summary(conv_id, new_exchange),
                                name="update_summary"
                            )
                    except Exception:
                        await db.rollback()

                yield f"data: {json.dumps({'type': 'conversation_id', 'id': conv_id}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"RAG stream error: {e}\n{_traceback.format_exc()}")
                yield f"data: {json.dumps({'type': 'error', 'msg': str(e)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(stream_with_images(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"RAG endpoint error (pre-stream): {e}\n{_traceback.format_exc()}")
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════
# 评测接口
# ═══════════════════════════════════════════════════════════════

class EvalRequest(BaseModel):
    strategy: Optional[str] = None
    summary_only: bool = False


@router.post("/eval", summary="运行 RAG 检索评测")
async def run_eval(
    req: EvalRequest = EvalRequest(),
    current_user: User = Depends(get_current_user),
):
    """运行检索评测，对比 BM25 / 向量 / 混合检索。summary_only=true 时仅返回摘要，不含逐题详情。"""
    return await eval_service.run_eval(summary_only=req.summary_only)


@router.get("/eval/questions", summary="获取评测问题列表")
async def get_eval_questions(current_user: User = Depends(get_current_user)):
    return {"total": len(eval_service.questions), "questions": eval_service.questions}


# ═══════════════════════════════════════════════════════════════
# 知识库管理接口
# ═══════════════════════════════════════════════════════════════

@router.get("/knowledge/stats", summary="知识库统计")
async def knowledge_stats(current_user: User = Depends(get_current_user)):
    from app.services.fitchef_loader import fitchef_loader
    return fitchef_loader.get_stats()


@router.post("/knowledge/build", summary="重建知识库索引")
async def knowledge_build(request: Request, current_user: User = Depends(get_current_user)):
    from app.services.fitchef_loader import fitchef_loader

    embedding = request.app.state.embedding_service
    if not embedding:
        raise HTTPException(status_code=503, detail="Embedding 服务未初始化")

    texts = fitchef_loader.get_texts()

    # BM25 重建
    hybrid_search_service.bm25.build_index(texts)

    # Milvus：先清空再全量插入
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, embedding.clear_collection)
    await embedding.create_embeddings_from_chunks(texts, filename="fitchef_knowledge")

    return {"status": "ok", "total": len(texts), "stats": fitchef_loader.get_stats()}


