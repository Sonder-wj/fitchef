# schemas/chat.py
# 职责：定义聊天接口的请求/响应格式

from pydantic import BaseModel
from app.models.conversation import DialogueType
from typing import Optional


class ChatSendRequest(BaseModel):
    """发送消息的请求体"""
    conversation_id: Optional[int] = None  # 不传则自动创建新对话
    message: str                            # 用户发的消息内容
    dialogue_type: DialogueType = DialogueType.NORMAL  # 对话类型


class ChatResponse(BaseModel):
    """非流式场景下的响应格式（流式用 StreamingResponse，不需要这个）"""
    conversation_id: int
    reply: str