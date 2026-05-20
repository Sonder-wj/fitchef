from sqlalchemy import Column, Integer, Enum, DateTime, ForeignKey, func
from app.core.database import Base
import enum


class GoalType(str, enum.Enum):
    CUT = "cut"
    BULK = "bulk"
    MAINTAIN = "maintain"


class UserGoal(Base):
    __tablename__ = "user_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    goal_type = Column(Enum(GoalType), nullable=False)
    daily_calories = Column(Integer, nullable=False)
    daily_protein_g = Column(Integer, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
