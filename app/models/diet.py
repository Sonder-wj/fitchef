from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class MealType(str, enum.Enum):
    BREAKFAST = "breakfast"  # 早餐
    LUNCH = "lunch"  # 午餐
    DINNER = "dinner"  # 晚餐
    SNACK = "snack"  # 加餐/零食


class DietMeal(Base):
    __tablename__ = "diet_meals"

    id = Column(Integer, primary_key=True, index=True)  # 主键，自增
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # 用户ID，关联 users 表；用户删除时级联删除其所有饮食记录
    date = Column(Date, nullable=False)  # 饮食日期
    meal_type = Column(Enum(MealType), nullable=False)  # 餐型：早餐/午餐/晚餐/加餐
    total_calories = Column(Float, nullable=False, default=0.0)  # 该餐总热量（千卡）
    total_protein = Column(Float, nullable=False, default=0.0)  # 该餐总蛋白质（克）
    total_fat = Column(Float, nullable=False, default=0.0)  # 该餐总脂肪（克）
    total_carbs = Column(Float, nullable=False, default=0.0)  # 该餐总碳水（克）
    created_at = Column(DateTime, server_default=func.now())  # 创建时间，由数据库自动填入

    # 关系
    items = relationship("DietFoodItem", back_populates="meal", cascade="all, delete-orphan")  # 一对多：一餐包含多个食物条目


class DietFoodItem(Base):
    __tablename__ = "diet_food_items"

    id = Column(Integer, primary_key=True, index=True)  # 主键，自增
    meal_id = Column(Integer, ForeignKey("diet_meals.id", ondelete="CASCADE"), nullable=False)  # 关联的餐食ID；餐食删除时级联删除其所有食物条目
    food_name = Column(String(100), nullable=False)  # 食物名称
    amount_g = Column(Float, nullable=False)  # 食用量（克）
    calories = Column(Float, nullable=False, default=0.0)  # 热量（千卡）
    protein_g = Column(Float, nullable=False, default=0.0)  # 蛋白质（克）
    fat_g = Column(Float, nullable=False, default=0.0)  # 脂肪（克）
    carbs_g = Column(Float, nullable=False, default=0.0)  # 碳水（克）

    # 关系
    meal = relationship("DietMeal", back_populates="items")  # 多对一：多个食物条目属于同一餐
