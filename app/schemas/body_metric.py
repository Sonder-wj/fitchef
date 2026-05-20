from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class BodyMetricCreate(BaseModel):
    """创建/编辑身体指标的请求体"""
    date: date
    weight_kg: float
    body_fat_pct: Optional[float] = None
    notes: Optional[str] = None


class BodyMetricOut(BaseModel):
    """身体指标响应"""
    id: int
    date: date
    weight_kg: float
    body_fat_pct: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
