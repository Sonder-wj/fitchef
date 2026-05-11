# schemas/message.py
# 职责：定义消息相关接口的数据格式

from pydantic import BaseModel
from datetime import datetime


class MessageResponse(BaseModel):
    """返回给前端的消息信息"""
    id: int
    conversation_id: int
    sender: str       # "user" 或 "assistant"
    content: str
    message_type: str
    created_at: datetime

    class Config:
        from_attributes = True  # 允许从 SQLAlchemy 对象直接转换
