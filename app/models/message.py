from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)  # 主键，自增
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"))  # 外键关联 conversations 表；会话删除时级联删除其所有消息
    sender = Column(String(50), nullable=False)  # 发送方，如 "user" 或 "assistant"
    content = Column(Text, nullable=False)  # 消息正文，Text 类型支持长文本
    created_at = Column(DateTime, server_default=func.now())  # 发送时间，由数据库自动填入
    message_type = Column(String(20), default="text")  # 消息类型，默认 "text"（预留扩展，如图片、文件等）

    # 关系
    conversation = relationship("Conversation", back_populates="messages")  # 多对一：多条消息属于同一个会话