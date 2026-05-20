from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.diet import DietMeal, DietFoodItem
from app.schemas.diet import DietMealCreate


class DietService:
    """饮食日志 CRUD 服务"""

    @staticmethod
    async def create(db: AsyncSession, user_id: int, data: DietMealCreate) -> DietMeal:
        """创建饮食记录（含食物条目，自动汇总营养素）"""
        total_cal = sum(i.calories for i in data.items)
        total_protein = sum(i.protein_g for i in data.items)
        total_fat = sum(i.fat_g for i in data.items)
        total_carbs = sum(i.carbs_g for i in data.items)

        meal = DietMeal(
            user_id=user_id,
            date=data.date,
            meal_type=data.meal_type,
            total_calories=total_cal,
            total_protein=total_protein,
            total_fat=total_fat,
            total_carbs=total_carbs,
        )
        db.add(meal)
        await db.flush()

        for item_data in data.items:
            item = DietFoodItem(
                meal_id=meal.id,
                food_name=item_data.food_name,
                amount_g=item_data.amount_g,
                calories=item_data.calories,
                protein_g=item_data.protein_g,
                fat_g=item_data.fat_g,
                carbs_g=item_data.carbs_g,
            )
            db.add(item)

        await db.commit()
        return await DietService._load_full(db, meal.id)

    @staticmethod
    async def list_meals(
        db: AsyncSession, user_id: int,
        start_date: Optional[str] = None, end_date: Optional[str] = None,
        limit: int = 30
    ) -> List[DietMeal]:
        """查询饮食记录列表（含食物条目）"""
        q = (
            select(DietMeal)
            .where(DietMeal.user_id == user_id)
            .options(selectinload(DietMeal.items))
            .order_by(DietMeal.date.desc(), DietMeal.id.desc())
            .limit(limit)
        )
        if start_date:
            q = q.where(DietMeal.date >= start_date)
        if end_date:
            q = q.where(DietMeal.date <= end_date)
        r = await db.execute(q)
        return r.scalars().all()

    @staticmethod
    async def _load_full(db: AsyncSession, meal_id: int) -> Optional[DietMeal]:
        """加载饮食记录及所有食物条目"""
        q = (
            select(DietMeal)
            .where(DietMeal.id == meal_id)
            .options(selectinload(DietMeal.items))
        )
        r = await db.execute(q)
        return r.scalar_one_or_none()

    @staticmethod
    async def get_detail(db: AsyncSession, user_id: int, meal_id: int) -> Optional[DietMeal]:
        """获取单条饮食记录详情"""
        meal = await DietService._load_full(db, meal_id)
        if not meal or meal.user_id != user_id:
            return None
        return meal

    @staticmethod
    async def update(
        db: AsyncSession, user_id: int, meal_id: int, data: DietMealCreate
    ) -> Optional[DietMeal]:
        """更新饮食记录（先删旧食物条目，再建新的）"""
        meal = await DietService._load_full(db, meal_id)
        if not meal or meal.user_id != user_id:
            return None

        meal.date = data.date
        meal.meal_type = data.meal_type
        meal.total_calories = sum(i.calories for i in data.items)
        meal.total_protein = sum(i.protein_g for i in data.items)
        meal.total_fat = sum(i.fat_g for i in data.items)
        meal.total_carbs = sum(i.carbs_g for i in data.items)

        for item in meal.items:
            await db.delete(item)
        for item_data in data.items:
            item = DietFoodItem(
                meal_id=meal.id,
                food_name=item_data.food_name,
                amount_g=item_data.amount_g,
                calories=item_data.calories,
                protein_g=item_data.protein_g,
                fat_g=item_data.fat_g,
                carbs_g=item_data.carbs_g,
            )
            db.add(item)

        await db.commit()
        return await DietService._load_full(db, meal.id)

    @staticmethod
    async def delete(db: AsyncSession, user_id: int, meal_id: int) -> bool:
        """删除饮食记录（级联删除食物条目）"""
        meal = await DietService._load_full(db, meal_id)
        if not meal or meal.user_id != user_id:
            return False
        await db.delete(meal)
        await db.commit()
        return True

    @staticmethod
    async def get_daily_summaries(
        db: AsyncSession, user_id: int, days: int = 30
    ) -> List[dict]:
        """获取每日营养摘要（按日期聚合）"""
        from datetime import date as dt, timedelta
        cutoff = dt.today() - timedelta(days=days)
        q = (
            select(DietMeal)
            .where(DietMeal.user_id == user_id, DietMeal.date >= cutoff)
            .order_by(DietMeal.date.asc())
        )
        r = await db.execute(q)
        meals = r.scalars().all()

        by_date = {}
        for m in meals:
            d = m.date.isoformat()
            if d not in by_date:
                by_date[d] = {"meals_count": 0, "total_calories": 0, "total_protein": 0, "total_fat": 0, "total_carbs": 0}
            by_date[d]["meals_count"] += 1
            by_date[d]["total_calories"] += m.total_calories
            by_date[d]["total_protein"] += m.total_protein
            by_date[d]["total_fat"] += m.total_fat
            by_date[d]["total_carbs"] += m.total_carbs

        result = []
        for date_str, totals in sorted(by_date.items()):
            result.append({
                "date": date_str,
                **{k: round(v, 1) for k, v in totals.items()},
            })
        return result

    @staticmethod
    async def get_nutrition_stats(
        db: AsyncSession, user_id: int, days: int = 7
    ) -> dict:
        """获取日均营养素统计（用于 Dashboard 和 RAG 交叉分析）"""
        summaries = await DietService.get_daily_summaries(db, user_id, days)
        if not summaries:
            return {
                "avg_daily_calories": 0, "avg_daily_protein": 0,
                "avg_daily_fat": 0, "avg_daily_carbs": 0,
            }
        n = len(summaries)
        return {
            "avg_daily_calories": round(sum(s["total_calories"] for s in summaries) / n, 1),
            "avg_daily_protein": round(sum(s["total_protein"] for s in summaries) / n, 1),
            "avg_daily_fat": round(sum(s["total_fat"] for s in summaries) / n, 1),
            "avg_daily_carbs": round(sum(s["total_carbs"] for s in summaries) / n, 1),
        }


diet_service = DietService()
