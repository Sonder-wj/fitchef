from sqlalchemy import Column, Integer, Enum, DateTime, ForeignKey, func
from app.core.database import Base
import enum


class GoalType(str, enum.Enum):
    CUT = "cut"  # 减脂
    BULK = "bulk"  # 增肌
    MAINTAIN = "maintain"  # 保持


class UserGoal(Base):
    __tablename__ = "user_goals"

    id = Column(Integer, primary_key=True, index=True)  # 主键，自增
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)  # 用户ID，关联 users 表，唯一约束确保每个用户只有一个目标
    goal_type = Column(Enum(GoalType), nullable=False)  # 目标类型：减脂/增肌/保持
    daily_calories = Column(Integer, nullable=False)  # 每日目标热量（千卡）
    daily_protein_g = Column(Integer, nullable=False)  # 每日目标蛋白质（克）
    created_at = Column(DateTime, server_default=func.now())  # 创建时间，由数据库自动填入
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # 更新时间，记录时自动填入，更新时自动刷新
