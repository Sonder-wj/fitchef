from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class DietFoodItemCreate(BaseModel):
    """创建食物条目的请求体"""
    food_name: str
    amount_g: float
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float


class DietFoodItemOut(BaseModel):
    """食物条目响应"""
    id: int
    food_name: str
    amount_g: float
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float

    class Config:
        from_attributes = True


class DietMealCreate(BaseModel):
    """创建/编辑饮食记录的请求体"""
    date: date
    meal_type: str  # breakfast/lunch/dinner/snack
    items: List[DietFoodItemCreate]


class DietMealOut(BaseModel):
    """饮食记录响应"""
    id: int
    user_id: int
    date: date
    meal_type: str
    total_calories: float
    total_protein: float
    total_fat: float
    total_carbs: float
    created_at: datetime
    items: List[DietFoodItemOut] = []

    class Config:
        from_attributes = True
