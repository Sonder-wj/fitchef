# schemas/conversation.py
# 职责：定义对话相关接口的数据格式

from pydantic import BaseModel
from datetime import datetime
from app.models.conversation import DialogueType


class ConversationCreate(BaseModel):
    """创建对话时前端传的数据"""
    dialogue_type: DialogueType = DialogueType.NORMAL  # 默认普通对话


class ConversationResponse(BaseModel):
    """返回给前端的对话信息"""
    id: int
    title: str
    status: str
    dialogue_type: DialogueType
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # 允许从 SQLAlchemy 对象直接转换