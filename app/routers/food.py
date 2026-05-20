from fastapi import APIRouter, Depends, Query
from app.core.security import get_current_user
from app.models.user import User
from app.services.food_db_service import food_db_service

router = APIRouter(prefix="/food", tags=["食物库"])


@router.get("/search", summary="搜索食物")
async def search_food(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """在 1657 种食物成分表中搜索，匹配食物名称"""
    items = food_db_service.search(q, limit=limit)
    return {"total": len(items), "items": items}


@router.get("/{food_id}", summary="食物详情")
async def get_food(
    food_id: str,
    current_user: User = Depends(get_current_user),
):
    """获取食物详细营养素（含微量元素）"""
    food = food_db_service.get_by_id(food_id)
    if not food:
        return {"detail": "食物不存在"}, 404
    return food
