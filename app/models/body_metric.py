from sqlalchemy import Column, Integer, Float, Date, DateTime, ForeignKey, Text, func
from app.core.database import Base


class BodyMetric(Base):
    __tablename__ = "body_metrics"

    id = Column(Integer, primary_key=True, index=True)  # 主键，自增
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # 用户ID，关联 users 表；用户删除时级联删除其所有身体指标
    date = Column(Date, nullable=False)  # 测量日期
    weight_kg = Column(Float, nullable=False)  # 体重（公斤）
    body_fat_pct = Column(Float, nullable=True)  # 体脂率（百分比），可为空
    notes = Column(Text, nullable=True)  # 备注，Text 类型支持长文本
    created_at = Column(DateTime, server_default=func.now())  # 创建时间，由数据库自动填入
