from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)  # 主键，自增
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # 用户ID，关联 users 表；用户删除时级联删除其所有训练记录
    date = Column(Date, nullable=False)  # 训练日期
    body_part = Column(String(40), nullable=False)  # 训练部位，如"胸"、"背"、"腿"、"肩+手臂"
    duration_min = Column(Integer, nullable=True)  # 训练时长（分钟）
    notes = Column(Text, nullable=True)  # 备注，Text 类型支持长文本
    created_at = Column(DateTime, server_default=func.now())  # 创建时间，由数据库自动填入

    # 关系
    exercises = relationship("WorkoutExercise", back_populates="workout", cascade="all, delete-orphan")  # 一对多：一次训练包含多个动作


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id = Column(Integer, primary_key=True, index=True)  # 主键，自增
    workout_id = Column(Integer, ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False)  # 关联的训练ID；训练删除时级联删除其所有动作
    exercise_name = Column(String(100), nullable=False)  # 动作名称，如"卧推"、"深蹲"
    sort_order = Column(Integer, nullable=False, default=0)  # 排序序号，用于控制动作在训练中的展示顺序

    # 关系
    workout = relationship("Workout", back_populates="exercises")  # 多对一：多个动作属于同一次训练
    sets = relationship("WorkoutSet", back_populates="exercise", cascade="all, delete-orphan")  # 一对多：一个动作包含多组


class WorkoutSet(Base):
    __tablename__ = "workout_sets"

    id = Column(Integer, primary_key=True, index=True)  # 主键，自增
    exercise_id = Column(Integer, ForeignKey("workout_exercises.id", ondelete="CASCADE"), nullable=False)  # 关联的动作ID；动作删除时级联删除其所有组
    set_number = Column(Integer, nullable=False)  # 组号，如第1组、第2组
    weight_kg = Column(Float, nullable=False, default=0.0)  # 重量（公斤）
    reps = Column(Integer, nullable=False, default=0)  # 次数

    # 关系
    exercise = relationship("WorkoutExercise", back_populates="sets")  # 多对一：多组属于同一个动作
