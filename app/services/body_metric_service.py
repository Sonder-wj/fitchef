from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.body_metric import BodyMetric
from app.schemas.body_metric import BodyMetricCreate


class BodyMetricService:
    """身体指标 CRUD 服务"""

    @staticmethod
    async def create(db: AsyncSession, user_id: int, data: BodyMetricCreate) -> BodyMetric:
        metric = BodyMetric(
            user_id=user_id,
            date=data.date,
            weight_kg=data.weight_kg,
            body_fat_pct=data.body_fat_pct,
            notes=data.notes,
        )
        db.add(metric)
        await db.commit()
        await db.refresh(metric)
        return metric

    @staticmethod
    async def list_metrics(
        db: AsyncSession, user_id: int, days: int = 90
    ) -> List[BodyMetric]:
        from datetime import date as dt, timedelta
        cutoff = dt.today() - timedelta(days=days)
        q = (
            select(BodyMetric)
            .where(BodyMetric.user_id == user_id, BodyMetric.date >= cutoff)
            .order_by(BodyMetric.date.asc())
        )
        r = await db.execute(q)
        return r.scalars().all()

    @staticmethod
    async def get_trend(db: AsyncSession, user_id: int, days: int = 90) -> dict:
        """计算体重趋势数据（用于图表和 RAG 交叉分析）"""
        metrics = await BodyMetricService.list_metrics(db, user_id, days)
        if not metrics:
            return {
                "dates": [], "weights": [], "body_fats": [],
                "weight_change": 0, "avg_weight": 0,
            }
        dates = [m.date.isoformat() for m in metrics]
        weights = [m.weight_kg for m in metrics]
        body_fats = [m.body_fat_pct for m in metrics]
        return {
            "dates": dates,
            "weights": weights,
            "body_fats": body_fats,
            "weight_change": round(weights[-1] - weights[0], 1),
            "avg_weight": round(sum(weights) / len(weights), 1),
        }

    @staticmethod
    async def update(
        db: AsyncSession, user_id: int, metric_id: int, data: BodyMetricCreate
    ) -> Optional[BodyMetric]:
        q = select(BodyMetric).where(BodyMetric.id == metric_id, BodyMetric.user_id == user_id)
        r = await db.execute(q)
        metric = r.scalar_one_or_none()
        if not metric:
            return None
        metric.date = data.date
        metric.weight_kg = data.weight_kg
        metric.body_fat_pct = data.body_fat_pct
        metric.notes = data.notes
        await db.commit()
        await db.refresh(metric)
        return metric

    @staticmethod
    async def delete(db: AsyncSession, user_id: int, metric_id: int) -> bool:
        q = select(BodyMetric).where(BodyMetric.id == metric_id, BodyMetric.user_id == user_id)
        r = await db.execute(q)
        metric = r.scalar_one_or_none()
        if not metric:
            return False
        await db.delete(metric)
        await db.commit()
        return True


body_metric_service = BodyMetricService()
