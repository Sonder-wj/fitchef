from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.schemas.workout import WorkoutCreate


class WorkoutService:
    """训练记录 CRUD 服务"""

    @staticmethod
    async def create(db: AsyncSession, user_id: int, data: WorkoutCreate) -> Workout:
        """创建训练记录（含动作和组）"""
        workout = Workout(
            user_id=user_id,
            date=data.date,
            body_part=data.body_part,
            duration_min=data.duration_min,
            notes=data.notes,
        )
        db.add(workout)
        await db.flush()

        for ex_data in data.exercises:
            exercise = WorkoutExercise(
                workout_id=workout.id,
                exercise_name=ex_data.exercise_name,
                sort_order=ex_data.sort_order,
            )
            db.add(exercise)
            await db.flush()

            for set_data in ex_data.sets:
                ws = WorkoutSet(
                    exercise_id=exercise.id,
                    set_number=set_data.set_number,
                    weight_kg=set_data.weight_kg,
                    reps=set_data.reps,
                )
                db.add(ws)

        await db.commit()
        await db.refresh(workout)
        return await WorkoutService._load_full(db, workout.id)

    @staticmethod
    async def list_workouts(
        db: AsyncSession, user_id: int,
        start_date: Optional[str] = None, end_date: Optional[str] = None,
        limit: int = 30
    ) -> List[dict]:
        """查询训练记录列表，返回摘要（含训练容量）"""
        q = select(Workout).where(Workout.user_id == user_id)
        if start_date:
            q = q.where(Workout.date >= start_date)
        if end_date:
            q = q.where(Workout.date <= end_date)
        q = q.order_by(Workout.date.desc()).limit(limit)
        r = await db.execute(q)
        workouts = r.scalars().all()

        summaries = []
        for w in workouts:
            ex_q = select(WorkoutExercise).where(WorkoutExercise.workout_id == w.id)
            ex_r = await db.execute(ex_q)
            exercises = ex_r.scalars().all()
            total_volume = 0.0
            for ex in exercises:
                set_q = select(WorkoutSet).where(WorkoutSet.exercise_id == ex.id)
                set_r = await db.execute(set_q)
                sets = set_r.scalars().all()
                for s in sets:
                    total_volume += s.weight_kg * s.reps
            summaries.append({
                "id": w.id,
                "date": w.date.isoformat(),
                "body_part": w.body_part,
                "exercise_count": len(exercises),
                "total_volume": round(total_volume, 1),
            })
        return summaries

    @staticmethod
    async def get_detail(db: AsyncSession, user_id: int, workout_id: int) -> Optional[Workout]:
        """获取训练记录详情（含动作和组）"""
        workout = await WorkoutService._load_full(db, workout_id)
        if not workout or workout.user_id != user_id:
            return None
        return workout

    @staticmethod
    async def _load_full(db: AsyncSession, workout_id: int) -> Optional[Workout]:
        """加载训练记录及所有关联数据"""
        q = (
            select(Workout)
            .where(Workout.id == workout_id)
            .options(
                selectinload(Workout.exercises).selectinload(WorkoutExercise.sets)
            )
        )
        r = await db.execute(q)
        return r.scalar_one_or_none()

    @staticmethod
    async def update(db: AsyncSession, user_id: int, workout_id: int, data: WorkoutCreate) -> Optional[Workout]:
        """更新训练记录（先删旧动作/组，再建新的）"""
        workout = await WorkoutService._load_full(db, workout_id)
        if not workout or workout.user_id != user_id:
            return None

        workout.date = data.date
        workout.body_part = data.body_part
        workout.duration_min = data.duration_min
        workout.notes = data.notes

        for ex in workout.exercises:
            for s in ex.sets:
                await db.delete(s)
            await db.delete(ex)

        for ex_data in data.exercises:
            exercise = WorkoutExercise(
                workout_id=workout.id,
                exercise_name=ex_data.exercise_name,
                sort_order=ex_data.sort_order,
            )
            db.add(exercise)
            await db.flush()
            for set_data in ex_data.sets:
                ws = WorkoutSet(
                    exercise_id=exercise.id,
                    set_number=set_data.set_number,
                    weight_kg=set_data.weight_kg,
                    reps=set_data.reps,
                )
                db.add(ws)

        await db.commit()
        return await WorkoutService._load_full(db, workout.id)

    @staticmethod
    async def delete(db: AsyncSession, user_id: int, workout_id: int) -> bool:
        """删除训练记录（级联删除动作和组）"""
        workout = await WorkoutService._load_full(db, workout_id)
        if not workout or workout.user_id != user_id:
            return False
        await db.delete(workout)
        await db.commit()
        return True

    @staticmethod
    async def get_exercise_names(db: AsyncSession, user_id: int) -> List[str]:
        """获取用户历史动作名列表（自动补全用）"""
        q = (
            select(WorkoutExercise.exercise_name)
            .join(Workout, Workout.id == WorkoutExercise.workout_id)
            .where(Workout.user_id == user_id)
            .distinct()
            .order_by(WorkoutExercise.exercise_name)
        )
        r = await db.execute(q)
        return [row[0] for row in r.all()]

    @staticmethod
    async def get_training_stats(
        db: AsyncSession, user_id: int, days: int = 30
    ) -> dict:
        """获取训练统计数据（用于 Dashboard 和 RAG 交叉分析）"""
        from datetime import date as dt, timedelta
        cutoff = dt.today() - timedelta(days=days)

        q = (
            select(Workout)
            .where(Workout.user_id == user_id, Workout.date >= cutoff)
            .options(
                selectinload(Workout.exercises).selectinload(WorkoutExercise.sets)
            )
            .order_by(Workout.date.asc())
        )
        r = await db.execute(q)
        workouts = r.scalars().all()

        total_sessions = len(workouts)
        volumes = []
        for w in workouts:
            vol = 0.0
            for ex in w.exercises:
                for s in ex.sets:
                    vol += s.weight_kg * s.reps
            volumes.append(round(vol, 1))

        return {
            "total_sessions": total_sessions,
            "frequency_per_week": round(total_sessions / (days / 7), 1),
            "volume_trend": volumes,
            "volume_change_pct": round(
                (volumes[-1] - volumes[0]) / volumes[0] * 100, 1
            ) if len(volumes) >= 2 and volumes[0] > 0 else 0,
        }


workout_service = WorkoutService()
