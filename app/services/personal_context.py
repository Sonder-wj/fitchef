from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.workout_service import workout_service
from app.services.body_metric_service import body_metric_service
from app.services.diet_service import diet_service


class PersonalContextBuilder:
    """构建用户个人数据摘要，用于 RAG 交叉分析"""

    @staticmethod
    async def build(
        db: AsyncSession,
        user_id: int,
        query: str,
    ) -> str:
        """从用户问题中提取时间范围，查三模块数据，返回结构化摘要"""
        parts = []

        # 从问题中提取时间范围
        days = 7
        if "一个月" in query or "近30天" in query or "这个月" in query:
            days = 30
        elif "两周" in query or "半个月" in query or "最近14天" in query:
            days = 14

        # 饮食统计
        nutrition = await diet_service.get_nutrition_stats(db, user_id, days)
        if nutrition.get("avg_daily_calories", 0) > 0:
            parts.append(f"- 日均热量摄入：{nutrition['avg_daily_calories']} kcal")
            parts.append(f"- 日均蛋白质：{nutrition['avg_daily_protein']}g")
            parts.append(f"- 日均脂肪：{nutrition['avg_daily_fat']}g")
            parts.append(f"- 日均碳水：{nutrition['avg_daily_carbs']}g")

        # 身体指标趋势
        trend = await body_metric_service.get_trend(db, user_id, days)
        if trend.get("weights"):
            first_w = trend["weights"][0]
            last_w = trend["weights"][-1]
            change = last_w - first_w
            direction = "↑" if change > 0 else ("↓" if change < 0 else "→")
            parts.append(f"- 体重变化：{first_w}kg → {last_w}kg（{direction}{abs(change):.1f}kg）")

        # 训练统计
        stats = await workout_service.get_training_stats(db, user_id, days)
        if stats.get("total_sessions", 0) > 0:
            parts.append(f"- 训练次数：{stats['total_sessions']}次（{stats['frequency_per_week']}次/周）")
            if stats.get("volume_change_pct") != 0:
                direction = "↑" if stats["volume_change_pct"] > 0 else "↓"
                parts.append(f"- 训练容量趋势：{direction}{abs(stats['volume_change_pct'])}%")

        if not parts:
            return "（暂无个人数据记录）"

        # 信号检测
        signals = []
        if nutrition.get("avg_daily_protein", 0) > 0 and nutrition["avg_daily_protein"] < 50:
            signals.append("- 蛋白质摄入偏低（日均不足50g），可能影响训练恢复")
        if trend.get("weights") and len(trend["weights"]) >= 2:
            change = trend["weights"][-1] - trend["weights"][0]
            if abs(change) < 0.3 and len(trend["weights"]) >= 7:
                signals.append("- 体重连续多天无明显变化，可能进入平台期")
        if stats.get("volume_change_pct", 0) < -10:
            signals.append("- 训练容量持续下降，提示恢复不足或热量缺口过大")

        signal_text = "\n".join(signals) if signals else "（未检测到明显异常信号）"

        return f"""【用户近况 最近{days}天】
{chr(10).join(parts)}

【关键信号】
{signal_text}"""


personal_context_builder = PersonalContextBuilder()
