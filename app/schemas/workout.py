from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class WorkoutSetCreate(BaseModel):
    """创建/编辑训练组的请求体"""
    set_number: int
    weight_kg: float = 0.0
    reps: int = 0


class WorkoutSetOut(BaseModel):
    """训练组响应"""
    id: int
    set_number: int
    weight_kg: float
    reps: int

    class Config:
        from_attributes = True


class WorkoutExerciseCreate(BaseModel):
    """创建/编辑训练动作的请求体"""
    exercise_name: str
    sort_order: int = 0
    sets: List[WorkoutSetCreate]


class WorkoutExerciseOut(BaseModel):
    """训练动作响应"""
    id: int
    exercise_name: str
    sort_order: int
    sets: List[WorkoutSetOut] = []

    class Config:
        from_attributes = True


class WorkoutCreate(BaseModel):
    """创建/编辑训练记录的请求体"""
    date: date
    body_part: str
    duration_min: Optional[int] = None
    notes: Optional[str] = None
    exercises: List[WorkoutExerciseCreate]


class WorkoutOut(BaseModel):
    """训练记录详情响应"""
    id: int
    user_id: int
    date: date
    body_part: str
    duration_min: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    exercises: List[WorkoutExerciseOut] = []

    class Config:
        from_attributes = True


class WorkoutSummary(BaseModel):
    """训练记录摘要（列表用）"""
    id: int
    date: date
    body_part: str
    exercise_count: int = 0
    total_volume: float = 0.0

    class Config:
        from_attributes = True
