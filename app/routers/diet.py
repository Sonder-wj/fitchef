from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.diet import DietMealCreate, DietMealOut
from app.services.diet_service import diet_service

router = APIRouter(prefix="/diet-meal", tags=["饮食日志"])


@router.post("", response_model=DietMealOut, summary="创建饮食记录")
async def create_meal(
    data: DietMealCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建饮食记录，含食物条目列表，自动汇总营养素"""
    return await diet_service.create(db, current_user.id, data)


@router.get("", summary="饮食记录列表")
async def list_meals(
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询登录用户的饮食记录 + 每日摘要"""
    meals = await diet_service.list_meals(db, current_user.id, start_date, end_date, limit)
    summaries = await diet_service.get_daily_summaries(db, current_user.id)
    return {"meals": meals, "daily_summaries": summaries}


@router.get("/{meal_id}", response_model=DietMealOut, summary="饮食详情")
async def get_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    m = await diet_service.get_detail(db, current_user.id, meal_id)
    if not m:
        return {"detail": "未找到"}, 404
    return m


@router.put("/{meal_id}", response_model=DietMealOut, summary="编辑饮食记录")
async def update_meal(
    meal_id: int,
    data: DietMealCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    m = await diet_service.update(db, current_user.id, meal_id, data)
    if not m:
        return {"detail": "未找到"}, 404
    return m


@router.delete("/{meal_id}", summary="删除饮食记录")
async def delete_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await diet_service.delete(db, current_user.id, meal_id)
    if not ok:
        return {"detail": "未找到"}, 404
    return {"message": "已删除"}
