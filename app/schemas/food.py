from pydantic import BaseModel
from typing import Optional


class FoodItem(BaseModel):
    id: str
    food_name: str
    calories: Optional[float] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbs: Optional[float] = None
    dietary_fiber: Optional[float] = None

    class Config:
        from_attributes = True


class FoodDetail(FoodItem):
    vitamin_c: Optional[str] = None
    vitamin_a: Optional[str] = None
    calcium: Optional[str] = None
    iron: Optional[str] = None
    zinc: Optional[str] = None
    potassium: Optional[str] = None
    remark: Optional[str] = None


class FoodSearchResponse(BaseModel):
    total: int
    items: list[FoodItem]
