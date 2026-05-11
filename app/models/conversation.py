from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Enum, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

#定义对话类型
class DialogueType(enum.Enum):
    NORMAL = "普通对话"
    RAG = "RAG 问答"

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)  # 主键，自增
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))  # 外键关联 users 表；用户删除时级联删除其所有会话
    title = Column(String(100), nullable=False)  # 会话标题，不允许为空
    summary = Column(Text, default="")  # 对话摘要，LLM 自动压缩历史为 2-3 句话
    created_at = Column(DateTime, server_default=func.now())  # 创建时间，由数据库自动填入当前时间
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # 更新时间，每次修改记录时自动刷新
    status = Column(String(20), default="ongoing")  # 会话状态，默认 "ongoing"（进行中）
    dialogue_type = Column(Enum(DialogueType), nullable=False)  # 对话类型，使用 DialogueType 枚举，不允许为空
#Enum(DialogueType) — 数据库层面限制，数据库里不能存非法值
    # 关系
    user = relationship("User", back_populates="conversations")  # 多对一：多个会话属于同一个用户
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")  # 一对多：一个会话包含多条消息；cascade 表示删除会话时自动删除其所有消息