from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.body_metric import BodyMetricCreate, BodyMetricOut
from app.services.body_metric_service import body_metric_service

router = APIRouter(prefix="/body-metric", tags=["身体指标"])


@router.post("", response_model=BodyMetricOut, summary="记录身体指标")
async def create_metric(
    data: BodyMetricCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """记录体重和体脂率"""
    return await body_metric_service.create(db, current_user.id, data)


@router.get("", summary="身体指标列表及趋势")
async def list_metrics(
    days: int = Query(90, ge=7, le=365, description="查询天数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指标列表 + 体重趋势数据（用于图表）"""
    metrics = await body_metric_service.list_metrics(db, current_user.id, days)
    trend = await body_metric_service.get_trend(db, current_user.id, days)
    return {"metrics": metrics, "trend": trend}


@router.put("/{metric_id}", response_model=BodyMetricOut, summary="编辑指标")
async def update_metric(
    metric_id: int,
    data: BodyMetricCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    m = await body_metric_service.update(db, current_user.id, metric_id, data)
    if not m:
        return {"detail": "未找到"}, 404
    return m


@router.delete("/{metric_id}", summary="删除指标")
async def delete_metric(
    metric_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await body_metric_service.delete(db, current_user.id, metric_id)
    if not ok:
        return {"detail": "未找到"}, 404
    return {"message": "已删除"}
