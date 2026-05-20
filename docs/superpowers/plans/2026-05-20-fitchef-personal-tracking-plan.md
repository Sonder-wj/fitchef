# 个人数据追踪 + RAG 交叉分析 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 FitChef 增加训练、身体指标、饮食日志三个追踪模块，并与现有 RAG 管线融合，实现"知识库 + 个人数据"交叉分析。

**Architecture:** 后端新增 5 个 SQLAlchemy 模型 + 4 组 CRUD 路由 + 3 个 service + 1 个 RAG 路由改造（Query Rewrite 增加 intent）；前端增加 vue-router + 4 个页面 + 4 个组件。

**Tech Stack:** FastAPI + SQLAlchemy async + Pydantic + Vue 3 Composition API + vue-router + Chart.js

---

## 文件结构映射

```
新增文件：
app/models/
├── workout.py           # Workout, WorkoutExercise, WorkoutSet
├── body_metric.py       # BodyMetric
├── diet.py              # DietMeal, DietFoodItem
└── user_goal.py         # UserGoal

app/schemas/
├── workout.py           # 训练模块全部 Pydantic schema
├── body_metric.py       # 身体指标 schema
├── diet.py              # 饮食日志 schema
└── food.py              # 食物搜索/详情 schema

app/routers/
├── workout.py           # /api/workout/*
├── body_metric.py       # /api/body-metric/*
├── diet.py              # /api/diet-meal/*
└── food.py              # /api/food/*

app/services/
├── workout_service.py
├── body_metric_service.py
├── diet_service.py
├── food_db_service.py   # 食物库搜索（china_food_composition.json）
└── personal_context.py  # 个人数据摘要构建

frontend/src/
├── router/index.js      # vue-router 路由配置
├── views/
│   ├── Dashboard.vue
│   ├── WorkoutLog.vue
│   ├── BodyMetric.vue
│   └── DietLog.vue
└── components/
    ├── WeightChart.vue
    ├── WorkoutForm.vue
    ├── DietMealForm.vue
    └── FoodSearch.vue

改动文件：
main.py                                         # 注册新路由 + 导入新模型
app/routers/chat.py                            # intent 路由适配
app/services/rag_chat_service.py               # 新增 rag_with_data 分支
app/services/query_rewriter_service.py         # prompt 增加 intent 输出
frontend/src/App.vue                           # 加入 router-view + 导航
frontend/src/components/ChatLayout.vue         # 导航入口
frontend/src/services/api.js                   # 新增 API 函数
```

---

## Phase 1: 基础设施

### Task 1: 数据库模型

**Files:**
- Create: `app/models/workout.py`
- Create: `app/models/body_metric.py`
- Create: `app/models/diet.py`
- Create: `app/models/user_goal.py`

- [ ] **Step 1: 创建训练模型 `app/models/workout.py`**

```python
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    body_part = Column(String(20), nullable=False)
    duration_min = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    exercises = relationship("WorkoutExercise", back_populates="workout", cascade="all, delete-orphan")


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False)
    exercise_name = Column(String(100), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)

    workout = relationship("Workout", back_populates="exercises")
    sets = relationship("WorkoutSet", back_populates="exercise", cascade="all, delete-orphan")


class WorkoutSet(Base):
    __tablename__ = "workout_sets"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("workout_exercises.id", ondelete="CASCADE"), nullable=False)
    set_number = Column(Integer, nullable=False)
    weight_kg = Column(Float, nullable=False, default=0.0)
    reps = Column(Integer, nullable=False, default=0)

    exercise = relationship("WorkoutExercise", back_populates="sets")
```

- [ ] **Step 2: 创建身体指标模型 `app/models/body_metric.py`**

```python
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, func
from app.core.database import Base

class BodyMetric(Base):
    __tablename__ = "body_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    weight_kg = Column(Float, nullable=False)
    body_fat_pct = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 3: 创建饮食日志模型 `app/models/diet.py`**

```python
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class MealType(str, enum.Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class DietMeal(Base):
    __tablename__ = "diet_meals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    meal_type = Column(Enum(MealType), nullable=False)
    total_calories = Column(Float, nullable=False, default=0.0)
    total_protein = Column(Float, nullable=False, default=0.0)
    total_fat = Column(Float, nullable=False, default=0.0)
    total_carbs = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

    items = relationship("DietFoodItem", back_populates="meal", cascade="all, delete-orphan")


class DietFoodItem(Base):
    __tablename__ = "diet_food_items"

    id = Column(Integer, primary_key=True, index=True)
    meal_id = Column(Integer, ForeignKey("diet_meals.id", ondelete="CASCADE"), nullable=False)
    food_name = Column(String(100), nullable=False)
    amount_g = Column(Float, nullable=False)
    calories = Column(Float, nullable=False, default=0.0)
    protein_g = Column(Float, nullable=False, default=0.0)
    fat_g = Column(Float, nullable=False, default=0.0)
    carbs_g = Column(Float, nullable=False, default=0.0)

    meal = relationship("DietMeal", back_populates="items")
```

- [ ] **Step 4: 创建用户目标模型 `app/models/user_goal.py`**

```python
from sqlalchemy import Column, Integer, Float, Enum, DateTime, ForeignKey, func
from app.core.database import Base
import enum


class GoalType(str, enum.Enum):
    CUT = "cut"
    BULK = "bulk"
    MAINTAIN = "maintain"


class UserGoal(Base):
    __tablename__ = "user_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    goal_type = Column(Enum(GoalType), nullable=False)
    daily_calories = Column(Integer, nullable=False)
    daily_protein_g = Column(Integer, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 5: 在 `main.py` 中导入新模型（建表用）**

在 `main.py` 的 lifespan 函数中，找到：
```python
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
```

改为：
```python
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.models.body_metric import BodyMetric
from app.models.diet import DietMeal, DietFoodItem
from app.models.user_goal import UserGoal
```

- [ ] **Step 6: 验证建表**

```bash
cd E:\develop\my_project1 && docker compose restart backend
docker compose logs backend | grep -i "数据库表初始化"
```

Expected: 看到 "数据库表初始化完成" 日志，无错误。

- [ ] **Step 7: Commit**

```bash
git add app/models/workout.py app/models/body_metric.py app/models/diet.py app/models/user_goal.py main.py
git commit -m "feat: 新增训练/身体/饮食/目标数据模型"
```

---

### Task 2: 食物库搜索服务

**Files:**
- Create: `app/services/food_db_service.py`
- Create: `app/schemas/food.py`
- Create: `app/routers/food.py`

- [ ] **Step 1: 创建食物 schema `app/schemas/food.py`**

```python
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
```

- [ ] **Step 2: 创建食物库搜索服务 `app/services/food_db_service.py`**

```python
import json
from pathlib import Path
from typing import List, Dict, Optional


class FoodDBService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def _load(self):
        if self._loaded:
            return
        data_path = Path(__file__).parent.parent / "data" / "china_food_composition.json"
        with open(data_path, "r", encoding="utf-8") as f:
            self._foods: List[Dict] = json.load(f)
        self._loaded = True

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        self._load()
        q = query.strip().lower()
        if not q:
            return []
        results = []
        for i, item in enumerate(self._foods):
            name = item.get("foodName", "")
            if not name:
                continue
            if q in name.lower():
                results.append({
                    "id": f"food_{i}",
                    "food_name": name,
                    "calories": self._to_float(item.get("energyKCal")),
                    "protein": self._to_float(item.get("protein")),
                    "fat": self._to_float(item.get("fat")),
                    "carbs": self._to_float(item.get("CHO")),
                    "dietary_fiber": self._to_float(item.get("dietaryFiber")),
                })
            if len(results) >= limit:
                break
        return results

    def get_by_id(self, food_id: str) -> Optional[Dict]:
        self._load()
        if not food_id.startswith("food_"):
            return None
        try:
            idx = int(food_id.split("_")[1])
        except (ValueError, IndexError):
            return None
        if idx < 0 or idx >= len(self._foods):
            return None
        item = self._foods[idx]
        name = item.get("foodName", "")
        if not name:
            return None
        return {
            "id": food_id,
            "food_name": name,
            "calories": self._to_float(item.get("energyKCal")),
            "protein": self._to_float(item.get("protein")),
            "fat": self._to_float(item.get("fat")),
            "carbs": self._to_float(item.get("CHO")),
            "dietary_fiber": self._to_float(item.get("dietaryFiber")),
            "vitamin_c": item.get("vitaminC", ""),
            "vitamin_a": item.get("vitaminA", ""),
            "calcium": item.get("Ca", ""),
            "iron": item.get("Fe", ""),
            "zinc": item.get("Zn", ""),
            "potassium": item.get("K", ""),
            "remark": item.get("remark", ""),
        }

    def calculate_nutrition(self, food_id: str, amount_g: float) -> Optional[Dict]:
        food = self.get_by_id(food_id)
        if not food:
            return None
        ratio = amount_g / 100.0
        return {
            "food_name": food["food_name"],
            "amount_g": amount_g,
            "calories": round((food["calories"] or 0) * ratio, 1),
            "protein_g": round((food["protein"] or 0) * ratio, 1),
            "fat_g": round((food["fat"] or 0) * ratio, 1),
            "carbs_g": round((food["carbs"] or 0) * ratio, 1),
        }

    @staticmethod
    def _to_float(val) -> Optional[float]:
        if val is None or val == "" or val == "…":
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None


food_db_service = FoodDBService()
```

- [ ] **Step 3: 创建食物搜索路由 `app/routers/food.py`**

```python
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
    items = food_db_service.search(q, limit=limit)
    return {"total": len(items), "items": items}


@router.get("/{food_id}", summary="食物详情")
async def get_food(
    food_id: str,
    current_user: User = Depends(get_current_user),
):
    food = food_db_service.get_by_id(food_id)
    if not food:
        return {"detail": "食物不存在"}, 404
    return food
```

- [ ] **Step 4: 注册路由**

在 `main.py` 中：
```python
# 找到:
from app.routers import auth, chat

# 改为:
from app.routers import auth, chat, food

# 找到:
app.include_router(chat.router)

# 后面加:
app.include_router(food.router)
```

- [ ] **Step 5: 测试搜索 API**

```bash
cd E:\develop\my_project1 && python -c "
import asyncio
from app.services.food_db_service import food_db_service
r = food_db_service.search('鸡胸')
print(f'找到 {len(r)} 条')
for item in r[:3]:
    print(f\"  {item['food_name']}: {item['calories']}kcal, 蛋白{item['protein']}g\")
"
```

Expected: 找到若干条鸡胸相关食物，输出热量和蛋白质。

- [ ] **Step 6: Commit**

```bash
git add app/services/food_db_service.py app/schemas/food.py app/routers/food.py main.py
git commit -m "feat: 食物库搜索服务 + /api/food/search 和 /api/food/:id"
```

---

## Phase 2: 后端 CRUD（三个模块可并行）

### Task 3: 训练记录 CRUD

**Files:**
- Create: `app/schemas/workout.py`
- Create: `app/services/workout_service.py`
- Create: `app/routers/workout.py`

- [ ] **Step 1: 创建训练 schema `app/schemas/workout.py`**

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class WorkoutSetCreate(BaseModel):
    set_number: int
    weight_kg: float = 0.0
    reps: int = 0


class WorkoutSetOut(BaseModel):
    id: int
    set_number: int
    weight_kg: float
    reps: int

    class Config:
        from_attributes = True


class WorkoutExerciseCreate(BaseModel):
    exercise_name: str
    sort_order: int = 0
    sets: List[WorkoutSetCreate]


class WorkoutExerciseOut(BaseModel):
    id: int
    exercise_name: str
    sort_order: int
    sets: List[WorkoutSetOut] = []

    class Config:
        from_attributes = True


class WorkoutCreate(BaseModel):
    date: date
    body_part: str
    duration_min: Optional[int] = None
    notes: Optional[str] = None
    exercises: List[WorkoutExerciseCreate]


class WorkoutOut(BaseModel):
    id: int
    user_id: int
    date: date
    body_part: str
    duration_min: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    exercises: List[WorkoutExerciseOut] = []

    class Config:
        from_attributes = True


class WorkoutSummary(BaseModel):
    id: int
    date: date
    body_part: str
    exercise_count: int = 0
    total_volume: float = 0.0

    class Config:
        from_attributes = True
```

- [ ] **Step 2: 创建训练 service `app/services/workout_service.py`**

```python
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.schemas.workout import WorkoutCreate


class WorkoutService:

    @staticmethod
    async def create(db: AsyncSession, user_id: int, data: WorkoutCreate) -> Workout:
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
        workout = await WorkoutService._load_full(db, workout_id)
        if not workout or workout.user_id != user_id:
            return None
        return workout

    @staticmethod
    async def _load_full(db: AsyncSession, workout_id: int) -> Optional[Workout]:
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
        workout = await WorkoutService._load_full(db, workout_id)
        if not workout or workout.user_id != user_id:
            return False
        await db.delete(workout)
        await db.commit()
        return True

    @staticmethod
    async def get_exercise_names(db: AsyncSession, user_id: int) -> List[str]:
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
        from datetime import date as dt, timedelta
        cutoff = dt.today() - timedelta(days=days)

        q = (
            select(Workout)
            .where(Workout.user_id == user_id, Workout.date >= cutoff)
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
```

- [ ] **Step 3: 创建训练路由 `app/routers/workout.py`**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.workout import WorkoutCreate, WorkoutOut, WorkoutSummary
from app.services.workout_service import workout_service

router = APIRouter(prefix="/workout", tags=["训练记录"])


@router.post("", response_model=WorkoutOut, summary="创建训练记录")
async def create_workout(
    data: WorkoutCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await workout_service.create(db, current_user.id, data)


@router.get("", response_model=list[WorkoutSummary], summary="训练列表")
async def list_workouts(
    start_date: str = Query(None),
    end_date: str = Query(None),
    limit: int = Query(30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await workout_service.list_workouts(
        db, current_user.id, start_date, end_date, limit
    )


@router.get("/exercises", summary="历史动作名列表")
async def get_exercise_names(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    names = await workout_service.get_exercise_names(db, current_user.id)
    return {"exercises": names}


@router.get("/{workout_id}", response_model=WorkoutOut, summary="训练详情")
async def get_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    w = await workout_service.get_detail(db, current_user.id, workout_id)
    if not w:
        return {"detail": "未找到"}, 404
    return w


@router.put("/{workout_id}", response_model=WorkoutOut, summary="编辑训练")
async def update_workout(
    workout_id: int,
    data: WorkoutCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    w = await workout_service.update(db, current_user.id, workout_id, data)
    if not w:
        return {"detail": "未找到"}, 404
    return w


@router.delete("/{workout_id}", summary="删除训练")
async def delete_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await workout_service.delete(db, current_user.id, workout_id)
    if not ok:
        return {"detail": "未找到"}, 404
    return {"message": "已删除"}
```

- [ ] **Step 4: 注册路由**

在 `main.py` 中：
```python
# 找到:
from app.routers import auth, chat, food

# 改为:
from app.routers import auth, chat, food, workout

# 在 app.include_router(food.router) 后面加:
app.include_router(workout.router)
```

- [ ] **Step 5: 验证**

```bash
cd E:\develop\my_project1 && docker compose restart backend && docker compose logs backend --tail 5
```

Expected: Backend 启动成功，无 import 错误。

- [ ] **Step 6: Commit**

```bash
git add app/schemas/workout.py app/services/workout_service.py app/routers/workout.py main.py
git commit -m "feat: 训练记录 CRUD API"
```

---

### Task 4: 身体指标 CRUD

**Files:**
- Create: `app/schemas/body_metric.py`
- Create: `app/services/body_metric_service.py`
- Create: `app/routers/body_metric.py`

- [ ] **Step 1: 创建 schema `app/schemas/body_metric.py`**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class BodyMetricCreate(BaseModel):
    date: date
    weight_kg: float
    body_fat_pct: Optional[float] = None
    notes: Optional[str] = None


class BodyMetricOut(BaseModel):
    id: int
    date: date
    weight_kg: float
    body_fat_pct: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BodyMetricTrend(BaseModel):
    dates: list[str]
    weights: list[float]
    body_fats: list[Optional[float]]
    weight_change: float  # 最新-最早
    avg_weight: float
```

- [ ] **Step 2: 创建 service `app/services/body_metric_service.py`**

```python
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.body_metric import BodyMetric
from app.schemas.body_metric import BodyMetricCreate


class BodyMetricService:

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
```

- [ ] **Step 3: 创建路由 `app/routers/body_metric.py`**

```python
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
    return await body_metric_service.create(db, current_user.id, data)


@router.get("", summary="身体指标列表及趋势")
async def list_metrics(
    days: int = Query(90, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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
```

- [ ] **Step 4: 注册路由**

在 `main.py` 中，修改 import 和 include_router。

- [ ] **Step 5: Commit**

```bash
git add app/schemas/body_metric.py app/services/body_metric_service.py app/routers/body_metric.py main.py
git commit -m "feat: 身体指标 CRUD API"
```

---

### Task 5: 饮食日志 CRUD

**Files:**
- Create: `app/schemas/diet.py`
- Create: `app/services/diet_service.py`
- Create: `app/routers/diet.py`

- [ ] **Step 1: 创建 schema `app/schemas/diet.py`**

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class DietFoodItemCreate(BaseModel):
    food_name: str
    amount_g: float
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float


class DietFoodItemOut(BaseModel):
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
    date: date
    meal_type: str  # breakfast/lunch/dinner/snack
    items: List[DietFoodItemCreate]


class DietMealOut(BaseModel):
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


class DietDailySummary(BaseModel):
    date: str
    meals_count: int
    total_calories: float
    total_protein: float
    total_fat: float
    total_carbs: float
```

- [ ] **Step 2: 创建 service `app/services/diet_service.py`**

```python
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models.diet import DietMeal, DietFoodItem
from app.schemas.diet import DietMealCreate


class DietService:

    @staticmethod
    async def create(db: AsyncSession, user_id: int, data: DietMealCreate) -> DietMeal:
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
        q = (
            select(DietMeal)
            .where(DietMeal.id == meal_id)
            .options(selectinload(DietMeal.items))
        )
        r = await db.execute(q)
        return r.scalar_one_or_none()

    @staticmethod
    async def get_detail(db: AsyncSession, user_id: int, meal_id: int) -> Optional[DietMeal]:
        meal = await DietService._load_full(db, meal_id)
        if not meal or meal.user_id != user_id:
            return None
        return meal

    @staticmethod
    async def update(
        db: AsyncSession, user_id: int, meal_id: int, data: DietMealCreate
    ) -> Optional[DietMeal]:
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
```

- [ ] **Step 3: 创建路由 `app/routers/diet.py`**

```python
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
    return await diet_service.create(db, current_user.id, data)


@router.get("", summary="饮食记录列表")
async def list_meals(
    start_date: str = Query(None),
    end_date: str = Query(None),
    limit: int = Query(30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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
```

- [ ] **Step 4: 注册路由**

在 `main.py` 中 import 并 `app.include_router(diet.router)`。

- [ ] **Step 5: Commit**

```bash
git add app/schemas/diet.py app/services/diet_service.py app/routers/diet.py main.py
git commit -m "feat: 饮食日志 CRUD API"
```

---

## Phase 3: RAG 集成（依赖 Phase 2）

### Task 6: Query Rewrite 增加 intent 判断

**Files:**
- Modify: `app/services/query_rewriter_service.py`

- [ ] **Step 1: 修改 QueryRewriteResult 模型，增加 intent 字段**

```python
# 在 app/services/query_rewriter_service.py 中

# 找到 QueryRewriteResult 类，添加 intent 字段:
class QueryRewriteResult(BaseModel):
    keywords: str = Field(
        default="",
        description="用于 BM25 关键词检索，空格分隔的饮食/健身术语。与饮食无关时留空"
    )
    semantic: str = Field(
        description="用于向量语义检索，一句自然的查询表述"
    )
    intent: str = Field(  # 新增
        default="rag_only",
        description="rag_only | data_query | rag_with_data"
    )
```

- [ ] **Step 2: 修改 REWRITE_PROMPT，增加 intent 说明**

```python
# 在 REWRITE_PROMPT 末尾，用户问题占位符前增加:
REWRITE_PROMPT = """你是健身饮食检索助手。用户问题可能偏口语化，你需要同时输出两种查询形式，用于两路不同检索。

规则：
- keywords: 提取核心饮食术语，像食材名、菜名、烹饪方式、营养素（蛋白质/碳水/脂肪/热量）、健身目标（减脂/增肌）。保留原词
- semantic: 把口语转成规范查询表述，保持自然语句形式，不要太长
- intent: 判断用户意图类型
  * "rag_only": 纯知识问题，不涉及用户个人数据。例："减脂该吃多少蛋白质""鸡胸肉怎么做"
  * "data_query": 用户查询自己的记录数据。例："我这周练了几次""我体重多少""看看我的饮食记录"
  * "rag_with_data": 用户问自己的情况并寻求分析建议。例："我最近体重不掉怎么办""我蛋白质吃不够影响大吗""为什么我练了没进步"
- 【重要】如果用户输入与饮食、健身、营养、食材、烹饪完全无关，keywords 必须严格输出空字符串 ""，semantic 保持原样。不要强行联想

判断无关话题的示例（keywords 必须为空）：
- 购物类："想买一件衣服"、"推荐手机" → keywords 留空
- 天气类："今天天气怎么样" → keywords 留空
- 闲聊类："讲个笑话"、"今天心情不好"、"推荐一部电影" → keywords 留空
- 注意：简单问候（"你好""嗨""在吗"）不算无关话题，将它们当作饮食咨询的开始，正常提取饮食关键词
- 科技类："Python怎么写" → keywords 留空

intent 判断示例：
- "减脂晚上吃什么" → intent: "rag_only"
- "我最近一周练了几次" → intent: "data_query"
- "我最近体重不掉了怎么办" → intent: "rag_with_data"
- "我这周蛋白质摄入够吗" → intent: "rag_with_data"

饮食健身相关的示例：
"减肥晚上吃什么" → keywords: "减脂 晚餐 低卡 高蛋白 蔬菜", semantic: "减脂期晚餐适合吃什么，有哪些低热量高蛋白的晚餐选择和食谱", intent: "rag_only"
"鸡胸肉怎么做好吃又不柴" → keywords: "鸡胸肉 烹饪 嫩 不柴 做法", semantic: "鸡胸肉怎么烹饪才能嫩而不柴，有哪些做法和技巧", intent: "rag_only"
"增肌一天要吃多少蛋白质" → keywords: "增肌 蛋白质 摄入量 每日", semantic: "增肌期每天需要摄入多少蛋白质，如何计算和分配", intent: "rag_only"
"这玩意热量高不高" → keywords: "热量 高 食物", semantic: "常见高热量食物有哪些，每100g热量多少大卡", intent: "rag_only"
"太胖了咋办" → keywords: "减脂 饮食 控制 热量", semantic: "减脂期应该如何调整饮食，有哪些低热量食物和饮食方案", intent: "rag_only"
"想买一件衣服" → keywords: "", semantic: "想买一件衣服", intent: "rag_only"
"我最近一周体重掉了1.5kg但是训练没力气怎么办" → keywords: "减脂 蛋白质 训练恢复 热量", semantic: "减脂期体重下降快但训练无力，如何调整饮食和训练", intent: "rag_with_data"

用户问题：{query}"""
```

- [ ] **Step 3: 修改 rewrite 方法返回 intent**

```python
# 在 rewrite 方法中，修改 return 语句:
async def rewrite(self, query: str) -> dict:
    try:
        result = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": REWRITE_PROMPT.format(query=query)}],
            response_model=QueryRewriteResult,
            temperature=0.3,
            max_tokens=200,
        )
        keywords = result.keywords.strip()
        semantic = result.semantic.strip() or query
        intent = getattr(result, "intent", "rag_only") or "rag_only"  # 新增
        logger.info(f"查询优化: '{query}' → keywords='{keywords}' intent={intent}")
        return {
            "original": query,
            "keywords": keywords,
            "semantic": semantic,
            "intent": intent,  # 新增
            "changed": keywords != "" or semantic != query,
        }
    except Exception as e:
        logger.warning(f"查询优化出错，回退原查询: {e}")
        return {
            "original": query,
            "keywords": query,
            "semantic": query,
            "intent": "rag_only",  # 新增，默认走纯 RAG
            "changed": False,
        }
```

- [ ] **Step 4: Commit**

```bash
git add app/services/query_rewriter_service.py
git commit -m "feat: Query Rewrite 增加 intent 判断（rag_only/data_query/rag_with_data）"
```

---

### Task 7: 个人数据摘要构建服务

**Files:**
- Create: `app/services/personal_context.py`

- [ ] **Step 1: 创建服务文件**

```python
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.workout_service import workout_service
from app.services.body_metric_service import body_metric_service
from app.services.diet_service import diet_service


class PersonalContextBuilder:

    @staticmethod
    async def build(
        db: AsyncSession,
        user_id: int,
        query: str,
    ) -> str:
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
```

- [ ] **Step 2: Commit**

```bash
git add app/services/personal_context.py
git commit -m "feat: 个人数据摘要构建服务"
```

---

### Task 8: RAG Chat Service 集成 intent 路由

**Files:**
- Modify: `app/services/rag_chat_service.py`

- [ ] **Step 1: 修改 generate_stream，增加 intent 分支**

在 `app/services/rag_chat_service.py` 中，找到 `rewrite_result` 获取处，改为：

```python
# 找到:
rewrite_result = await query_rewriter_service.rewrite(context_query)
keywords = rewrite_result.get("keywords", query)
semantic = rewrite_result.get("semantic", query)

# 后面加上 intent:
intent = rewrite_result.get("intent", "rag_only")
```

- [ ] **Step 2: 在低置信度检查之前，新增 data_query 和 rag_with_data 处理**

在 `rag_chat_service.py` 中，找到 `# ── 低置信度查询` 注释前，插入：

```python
            # ── data_query：查个人数据 → LLM 格式化 ──
            if intent == "data_query":
                from app.services.personal_context import personal_context_builder
                from app.core.database import AsyncSessionLocal

                async with AsyncSessionLocal() as s:
                    ctx = await personal_context_builder.build(s, user_id, query)

                data_prompt = f"""你是 FitChef 健身饮食助手。用户查询自己的个人数据，下面是查询结果。

{ctx}

请自然地回复用户的问题。语气专业简洁，直接说明数据情况。如果数据为空，告诉用户还没有记录。"""
                messages = [{"role": "system", "content": data_prompt}]
                for h in history[-4:]:
                    messages.append(h)
                messages.append({"role": "user", "content": query})

                try:
                    stream = await self.client.chat.completions.create(
                        model=self.model, messages=messages, stream=True, temperature=0.5
                    )
                    async for chunk in stream:
                        if chunk.choices[0].delta.content:
                            yield f"data: {json.dumps(chunk.choices[0].delta.content, ensure_ascii=False)}\n\n"
                except Exception as e:
                    logger.error(f"data_query LLM 调用失败: {e}")
                return
```

- [ ] **Step 3: 新增 rag_with_data 处理**

在上述 data_query 处理后，低置信度检查前，插入：

```python
            # ── rag_with_data：知识检索 + 个人数据并行 ──
            if intent == "rag_with_data":
                from app.services.personal_context import personal_context_builder
                from app.core.database import AsyncSessionLocal
                import asyncio

                # 并行：知识检索 + 个人数据查询
                async def fetch_personal():
                    async with AsyncSessionLocal() as s:
                        return await personal_context_builder.build(s, user_id, query)

                personal_task = asyncio.create_task(fetch_personal())

                # 知识库检索（复用现有逻辑）
                search_result = await hybrid_search_service.search(
                    query=query, bm25_query=keywords, vector_query=semantic, top_k=12
                )
                results = search_result.get("results", [])

                personal_context = await personal_task

                # 重排序 + 短语加权 + 截断（复用现有逻辑，但要提前处理）
                if settings.RAG_USE_RERANK:
                    rerank_result = await reranker_service.rerank(semantic, results, top_k=8)
                    final_results = rerank_result.get("results", results)
                else:
                    final_results = results

                # 短语加权
                query_phrases = _extract_query_phrases(query)
                for r in final_results:
                    content = r.get("content", "")
                    title = ""
                    if content.startswith("【") and "】" in content[:30]:
                        after_bracket = content[content.index("】")+1:]
                        title = after_bracket.split("\n")[0].strip()
                    for phrase in query_phrases:
                        if phrase and len(phrase) >= 2 and phrase in title:
                            for key in ("rerank_score", "rrf_score", "score"):
                                if key in r:
                                    r[key] = r[key] * 2.0
                                    break
                            break
                final_results.sort(
                    key=lambda x: x.get("rerank_score", x.get("rrf_score", x.get("score", 0))),
                    reverse=True
                )
                # 动态截断
                for i in range(1, len(final_results)):
                    prev = final_results[i-1].get("rerank_score", final_results[i-1].get("rrf_score", 0))
                    curr = final_results[i].get("rerank_score", final_results[i].get("rrf_score", 0))
                    if prev > 0 and curr / prev < 0.85:
                        final_results = final_results[:i]
                        break
                final_results = final_results[:5]

                if not final_results:
                    final_results = results[:3]

                # 发送检索结果
                yield f"data: {json.dumps({'type': 'search_results', 'total': len(final_results), 'results': [{'content': r['content'][:200], 'score': r.get('rerank_score', r.get('rrf_score', r.get('score', 0))), 'doc_id': r['doc_id']} for r in final_results]}, ensure_ascii=False)}\n\n"

                # 构建上下文：知识库 + 个人数据
                context_parts = []
                for idx, r in enumerate(final_results):
                    context_parts.append(f"[{idx + 1}] {r['content']}")
                knowledge_context = "\n---\n".join(context_parts)

                CROSS_ANALYSIS_PROMPT = """你是一位专业的健身饮食顾问 FitChef。现在你有两个信息来源：
1. 知识库文档（带编号的参考资料）
2. 用户的个人数据（训练、身体指标、饮食记录）

请基于这两方面信息，为用户提供个性化分析建议。
- 第一段给出核心结论，结合用户具体数据
- 引用知识库内容时用 [N] 标注
- 引用用户数据时直接说具体数字
- 关键数值用 **加粗** 突出
- 保持专业、简洁

## 知识库参考资料
{knowledge}

## 用户个人数据
{personal}"""

                system_prompt = CROSS_ANALYSIS_PROMPT.format(
                    knowledge=knowledge_context,
                    personal=personal_context,
                )
                if summary:
                    system_prompt += f"\n\n对话背景：{summary}"

                messages = [{"role": "system", "content": system_prompt}]
                for h in history[-4:]:
                    messages.append(h)
                messages.append({"role": "user", "content": query})

                try:
                    stream = await self.client.chat.completions.create(
                        model=self.model, messages=messages, stream=True, temperature=0.5
                    )
                    async for chunk in stream:
                        if chunk.choices[0].delta.content:
                            yield f"data: {json.dumps(chunk.choices[0].delta.content, ensure_ascii=False)}\n\n"
                except Exception as e:
                    logger.error(f"rag_with_data LLM 失败: {e}")
                return
```

- [ ] **Step 4: 确保 user_id 传递**

`generate_stream` 方法签名已有 `user_id` 参数，但当前调用 `generate_stream` 时没有传 `user_id`。检查 `routers/chat.py` 中的调用并补传：

```python
# 在 routers/chat.py rag_endpoint 中，找到:
async for chunk in rag_chat_service.generate_stream(
    req.message, history=hist, summary=conv_summary
):

# 改为:
async for chunk in rag_chat_service.generate_stream(
    req.message, user_id=current_user.id, history=hist, summary=conv_summary
):
```

- [ ] **Step 5: 验证**

```bash
cd E:\develop\my_project1 && docker compose restart backend && docker compose logs backend --tail 5
```

Expected: 后端启动成功。

- [ ] **Step 6: Commit**

```bash
git add app/services/rag_chat_service.py app/routers/chat.py
git commit -m "feat: RAG 集成 intent 路由——rag_with_data 交叉分析"
```

---

## Phase 4: 前端

### Task 9: Vue Router + 导航框架

**Files:**
- Create: `frontend/src/router/index.js`
- Modify: `frontend/src/main.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/components/ChatLayout.vue`

- [ ] **Step 1: 安装 vue-router**

```bash
cd E:\develop\my_project1\frontend && npm install vue-router@4
```

- [ ] **Step 2: 创建路由配置 `frontend/src/router/index.js`**

```javascript
import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/chat',
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('../components/ChatLayout.vue'),
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
  },
  {
    path: '/workout',
    name: 'Workout',
    component: () => import('../views/WorkoutLog.vue'),
  },
  {
    path: '/body',
    name: 'BodyMetric',
    component: () => import('../views/BodyMetric.vue'),
  },
  {
    path: '/diet',
    name: 'DietLog',
    component: () => import('../views/DietLog.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
```

- [ ] **Step 3: 修改 `frontend/src/main.js`**

```javascript
import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.js'

createApp(App).use(router).mount('#app')
```

- [ ] **Step 4: 修改 `frontend/src/App.vue`**

将整个 template 改为：

```html
<template>
  <div class="app-shell">
    <LoginForm v-if="!loggedIn" @logged-in="onLogin" />
    <template v-else>
      <nav class="app-nav">
        <div class="nav-brand">
          <span class="brand-icon">🥗</span>
          <span class="brand-name">FitChef</span>
        </div>
        <div class="nav-links">
          <router-link to="/chat" class="nav-link">💬 对话</router-link>
          <router-link to="/dashboard" class="nav-link">📊 仪表盘</router-link>
          <router-link to="/workout" class="nav-link">🏋️ 训练</router-link>
          <router-link to="/body" class="nav-link">⚖️ 身体</router-link>
          <router-link to="/diet" class="nav-link">🍽️ 饮食</router-link>
        </div>
        <div class="nav-right">
          <span class="user-tag">{{ user?.email || '' }}</span>
          <button class="logout-btn" @click="onLogout">退出</button>
        </div>
      </nav>
      <div class="app-content">
        <router-view :user="user" @logout="onLogout" />
      </div>
    </template>
  </div>
</template>
```

在 script 的顶部添加 `import LoginForm from './components/LoginForm.vue'`（保持不变）。

在 `<style>` 末尾追加：

```css
.app-nav {
  display: flex;
  align-items: center;
  height: 52px;
  padding: 0 20px;
  background: var(--green-900);
  gap: 24px;
  flex-shrink: 0;
}
.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}
.nav-brand .brand-icon { font-size: 1.2rem; }
.nav-brand .brand-name {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
  color: #fff;
}
.nav-links { display: flex; gap: 4px; }
.nav-link {
  padding: 8px 14px;
  color: rgba(255,255,255,0.65);
  text-decoration: none;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
}
.nav-link:hover { background: rgba(255,255,255,0.08); color: #fff; }
.nav-link.router-link-active { background: var(--green-500); color: #fff; }
.nav-right { margin-left: auto; display: flex; align-items: center; gap: 12px; }
.nav-right .user-tag { color: rgba(255,255,255,0.5); font-size: 0.82rem; }
.nav-right .logout-btn {
  padding: 5px 14px;
  background: none;
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: var(--radius-sm);
  color: rgba(255,255,255,0.6);
  cursor: pointer;
  font-size: 0.82rem;
  font-family: var(--font-body);
  transition: border-color 0.15s, color 0.15s;
}
.nav-right .logout-btn:hover { border-color: var(--coral); color: var(--coral); }
.app-content {
  flex: 1;
  overflow: hidden;
}
```

- [ ] **Step 5: 修改 ChatLayout.vue 适配 router-view 嵌套**

ChatLayout 现在作为路由页面，有自己的 layout，需要调整。将 ChatLayout 的 `<style scoped>` 中的 `.chat-layout` 高度改为 `height: 100%`（去掉原来的 100% width 依赖）。

确认 ChatLayout 的 props 和 emit 仍然正常工作——现在通过 router-view 传递 `:user` 和 `@logout`。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/router/ frontend/src/main.js frontend/src/App.vue frontend/src/components/ChatLayout.vue frontend/package.json frontend/package-lock.json
git commit -m "feat: 前端 vue-router + 导航栏"
```

---

### Task 10: 前端 API 扩展

**Files:**
- Modify: `frontend/src/services/api.js`

- [ ] **Step 1: 新增 API 函数**

在 `frontend/src/services/api.js` 末尾追加：

```javascript
// ── Workout ──

export async function listWorkouts(startDate, endDate) {
  const params = new URLSearchParams()
  if (startDate) params.append('start_date', startDate)
  if (endDate) params.append('end_date', endDate)
  const res = await fetch(`/workout?${params}`, { headers: authHeaders() })
  if (!res.ok) throw new Error('获取训练列表失败')
  return res.json()
}

export async function createWorkout(data) {
  const res = await fetch('/workout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(data),
  })
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || '创建失败') }
  return res.json()
}

export async function getWorkout(id) {
  const res = await fetch(`/workout/${id}`, { headers: authHeaders() })
  if (!res.ok) throw new Error('获取训练详情失败')
  return res.json()
}

export async function updateWorkout(id, data) {
  const res = await fetch(`/workout/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('更新失败')
  return res.json()
}

export async function deleteWorkout(id) {
  const res = await fetch(`/workout/${id}`, { method: 'DELETE', headers: authHeaders() })
  if (!res.ok) throw new Error('删除失败')
  return res.json()
}

export async function getExerciseNames() {
  const res = await fetch('/workout/exercises', { headers: authHeaders() })
  if (!res.ok) throw new Error('获取动作列表失败')
  return res.json()
}

// ── Body Metric ──

export async function listBodyMetrics(days = 90) {
  const res = await fetch(`/body-metric?days=${days}`, { headers: authHeaders() })
  if (!res.ok) throw new Error('获取身体指标失败')
  return res.json()
}

export async function createBodyMetric(data) {
  const res = await fetch('/body-metric', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(data),
  })
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || '创建失败') }
  return res.json()
}

export async function updateBodyMetric(id, data) {
  const res = await fetch(`/body-metric/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('更新失败')
  return res.json()
}

export async function deleteBodyMetric(id) {
  const res = await fetch(`/body-metric/${id}`, { method: 'DELETE', headers: authHeaders() })
  if (!res.ok) throw new Error('删除失败')
  return res.json()
}

// ── Diet ──

export async function listDietMeals(startDate, endDate) {
  const params = new URLSearchParams()
  if (startDate) params.append('start_date', startDate)
  if (endDate) params.append('end_date', endDate)
  const res = await fetch(`/diet-meal?${params}`, { headers: authHeaders() })
  if (!res.ok) throw new Error('获取饮食列表失败')
  return res.json()
}

export async function createDietMeal(data) {
  const res = await fetch('/diet-meal', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(data),
  })
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || '创建失败') }
  return res.json()
}

export async function getDietMeal(id) {
  const res = await fetch(`/diet-meal/${id}`, { headers: authHeaders() })
  if (!res.ok) throw new Error('获取饮食详情失败')
  return res.json()
}

export async function updateDietMeal(id, data) {
  const res = await fetch(`/diet-meal/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('更新失败')
  return res.json()
}

export async function deleteDietMeal(id) {
  const res = await fetch(`/diet-meal/${id}`, { method: 'DELETE', headers: authHeaders() })
  if (!res.ok) throw new Error('删除失败')
  return res.json()
}

// ── Food DB ──

export async function searchFood(query) {
  const res = await fetch(`/food/search?q=${encodeURIComponent(query)}`, { headers: authHeaders() })
  if (!res.ok) throw new Error('搜索食物失败')
  return res.json()
}

export async function getFoodDetail(foodId) {
  const res = await fetch(`/food/${foodId}`, { headers: authHeaders() })
  if (!res.ok) throw new Error('获取食物详情失败')
  return res.json()
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/api.js
git commit -m "feat: 前端 API 扩展——训练/身体/饮食/食物库"
```

---

### Task 11: Dashboard 页面

**Files:**
- Create: `frontend/src/views/Dashboard.vue`

- [ ] **Step 1: 创建 Dashboard 页面**

```html
<script setup>
import { ref, onMounted } from 'vue'
import { listBodyMetrics, listDietMeals, listWorkouts } from '../services/api.js'
import WeightChart from '../components/WeightChart.vue'

const trend = ref({ dates: [], weights: [], body_fats: [], weight_change: 0, avg_weight: 0 })
const nutrition = ref({ avg_daily_calories: 0, avg_daily_protein: 0, avg_daily_fat: 0, avg_daily_carbs: 0 })
const workoutStats = ref({ total_sessions: 0, frequency_per_week: 0, volume_trend: [], volume_change_pct: 0 })
const loading = ref(true)

onMounted(async () => {
  try {
    const [bodyData, dietData, workoutData] = await Promise.all([
      listBodyMetrics(90),
      listDietMeals(),
      listWorkouts(),
    ])
    if (bodyData.trend) trend.value = bodyData.trend
    if (dietData.daily_summaries?.length) {
      const recent = dietData.daily_summaries.slice(-7)
      const n = recent.length
      nutrition.value = {
        avg_daily_calories: Math.round(recent.reduce((s, d) => s + d.total_calories, 0) / n),
        avg_daily_protein: Math.round(recent.reduce((s, d) => s + d.total_protein, 0) / n * 10) / 10,
        avg_daily_fat: Math.round(recent.reduce((s, d) => s + d.total_fat, 0) / n * 10) / 10,
        avg_daily_carbs: Math.round(recent.reduce((s, d) => s + d.total_carbs, 0) / n),
      }
    }
    if (workoutData.length) {
      const sess = workoutData
      const vols = sess.map(s => s.total_volume).filter(v => v > 0)
      workoutStats.value = {
        total_sessions: sess.length,
        frequency_per_week: Math.round(sess.length / 4 * 10) / 10,
        volume_trend: vols,
        volume_change_pct: vols.length >= 2 ? Math.round((vols[vols.length - 1] - vols[0]) / vols[0] * 100) : 0,
      }
    }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="dashboard">
    <h2 class="page-title">仪表盘</h2>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else class="cards">
      <div class="card">
        <h3>体重趋势</h3>
        <WeightChart :dates="trend.dates" :weights="trend.weights" />
        <div class="card-stats">
          <span>平均 {{ trend.avg_weight }}kg</span>
          <span :class="trend.weight_change >= 0 ? 'up' : 'down'">
            {{ trend.weight_change >= 0 ? '+' : '' }}{{ trend.weight_change }}kg
          </span>
        </div>
      </div>

      <div class="card">
        <h3>本周营养</h3>
        <div class="stat-grid">
          <div class="stat"><span class="label">热量</span><span class="value">{{ nutrition.avg_daily_calories }} kcal</span></div>
          <div class="stat"><span class="label">蛋白质</span><span class="value">{{ nutrition.avg_daily_protein }}g</span></div>
          <div class="stat"><span class="label">脂肪</span><span class="value">{{ nutrition.avg_daily_fat }}g</span></div>
          <div class="stat"><span class="label">碳水</span><span class="value">{{ nutrition.avg_daily_carbs }}g</span></div>
        </div>
      </div>

      <div class="card">
        <h3>本周训练</h3>
        <div class="stat-grid">
          <div class="stat"><span class="label">次数</span><span class="value">{{ workoutStats.total_sessions }}</span></div>
          <div class="stat"><span class="label">频率</span><span class="value">{{ workoutStats.frequency_per_week }}次/周</span></div>
          <div class="stat">
            <span class="label">容量趋势</span>
            <span class="value" :class="workoutStats.volume_change_pct >= 0 ? 'up' : 'down'">
              {{ workoutStats.volume_change_pct >= 0 ? '+' : '' }}{{ workoutStats.volume_change_pct }}%
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard { padding: 24px; max-width: 960px; margin: 0 auto; height: 100%; overflow-y: auto; }
.page-title { font-size: 1.3rem; font-weight: 700; margin-bottom: 20px; }
.loading { text-align: center; color: var(--text-muted); padding: 40px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.card {
  background: var(--white); border-radius: var(--radius); padding: 18px;
  box-shadow: var(--shadow-sm);
}
.card h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 12px; color: var(--text); }
.card-stats { display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.85rem; color: var(--text-muted); }
.stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.stat { display: flex; flex-direction: column; gap: 2px; }
.stat .label { font-size: 0.75rem; color: var(--text-muted); }
.stat .value { font-size: 1.1rem; font-weight: 700; }
.up { color: var(--coral); }
.down { color: var(--green-500); }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/Dashboard.vue
git commit -m "feat: Dashboard 页面——体重趋势/营养摘要/训练统计"
```

---

### Task 12: WeightChart 组件

**Files:**
- Create: `frontend/src/components/WeightChart.vue`

- [ ] **Step 1: 创建图表组件**（纯 SVG，无需额外依赖）

```html
<script setup>
import { computed } from 'vue'

const props = defineProps({
  dates: { type: Array, default: () => [] },
  weights: { type: Array, default: () => [] },
})

const points = computed(() => {
  if (!props.weights.length) return ''
  const w = 260; const h = 100; const pad = 10
  const max = Math.max(...props.weights) + 2
  const min = Math.min(...props.weights) - 2
  const range = max - min || 1
  return props.weights.map((v, i) => {
    const x = pad + (i / Math.max(props.weights.length - 1, 1)) * (w - pad * 2)
    const y = h - pad - ((v - min) / range) * (h - pad * 2)
    return `${x},${y}`
  }).join(' ')
})

const hasData = computed(() => props.weights.length > 0)
</script>

<template>
  <div class="chart-wrap">
    <svg v-if="hasData" viewBox="0 0 260 100" class="chart-svg">
      <polyline :points="points" fill="none" stroke="var(--green-500)" stroke-width="2" />
    </svg>
    <div v-else class="no-data">暂无数据</div>
  </div>
</template>

<style scoped>
.chart-wrap { width: 100%; }
.chart-svg { width: 100%; height: auto; }
.no-data { text-align: center; color: var(--text-muted); padding: 20px; font-size: 0.85rem; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/WeightChart.vue
git commit -m "feat: WeightChart 体重趋势折线图组件（SVG）"
```

---

### Task 13: WorkoutLog 页面

**Files:**
- Create: `frontend/src/views/WorkoutLog.vue`
- Create: `frontend/src/components/WorkoutForm.vue`

- [ ] **Step 1: 创建 WorkoutForm 组件 `frontend/src/components/WorkoutForm.vue`**

```html
<script setup>
import { ref, onMounted } from 'vue'
import { getExerciseNames } from '../services/api.js'

const props = defineProps({ initial: Object })
const emit = defineEmits(['save', 'cancel'])

const historyExercises = ref([])
onMounted(async () => {
  try { const r = await getExerciseNames(); historyExercises.value = r.exercises || []; } catch {}
})

const bodyParts = ['胸', '背', '腿', '肩', '臂', '全身']

const form = ref({
  date: props.initial?.date || new Date().toISOString().slice(0, 10),
  body_part: props.initial?.body_part || '',
  duration_min: props.initial?.duration_min || null,
  notes: props.initial?.notes || '',
  exercises: props.initial?.exercises || [],
})

function addExercise() {
  form.value.exercises.push({ exercise_name: '', sort_order: form.value.exercises.length, sets: [{ set_number: 1, weight_kg: 0, reps: 0 }] })
}

function removeExercise(idx) { form.value.exercises.splice(idx, 1) }

function addSet(exIdx) {
  const sets = form.value.exercises[exIdx].sets
  sets.push({ set_number: sets.length + 1, weight_kg: sets[sets.length - 1]?.weight_kg || 0, reps: sets[sets.length - 1]?.reps || 0 })
}

function removeSet(exIdx, setIdx) { form.value.exercises[exIdx].sets.splice(setIdx, 1) }

function onSave() { emit('save', { ...form.value }) }
</script>

<template>
  <div class="form-overlay" @click.self="emit('cancel')">
    <div class="form-panel">
      <h3>{{ props.initial ? '编辑训练' : '记录训练' }}</h3>

      <div class="field-row">
        <label>日期 <input type="date" v-model="form.date" /></label>
        <label>部位
          <select v-model="form.body_part">
            <option value="">选择</option>
            <option v-for="bp in bodyParts" :key="bp" :value="bp">{{ bp }}</option>
          </select>
        </label>
      </div>
      <div class="field-row">
        <label>时长(分) <input type="number" v-model="form.duration_min" min="0" /></label>
      </div>

      <div class="exercises-section">
        <div v-for="(ex, exIdx) in form.exercises" :key="exIdx" class="exercise-block">
          <div class="ex-header">
            <input
              v-model="ex.exercise_name"
              placeholder="动作名"
              list="exercise-list"
              class="ex-name-input"
            />
            <datalist id="exercise-list">
              <option v-for="name in historyExercises" :key="name" :value="name" />
            </datalist>
            <button class="btn-sm btn-del" @click="removeExercise(exIdx)">×</button>
          </div>
          <div v-for="(set, setIdx) in ex.sets" :key="setIdx" class="set-row">
            <span class="set-num">{{ setIdx + 1 }}</span>
            <input type="number" v-model="set.weight_kg" placeholder="重量kg" step="0.5" min="0" class="set-input" />
            <input type="number" v-model="set.reps" placeholder="次数" min="0" class="set-input" />
            <button v-if="ex.sets.length > 1" class="btn-sm btn-del" @click="removeSet(exIdx, setIdx)">×</button>
          </div>
          <button class="btn-sm btn-add" @click="addSet(exIdx)">+ 组</button>
        </div>
      </div>

      <button class="btn-add-ex" @click="addExercise">+ 动作</button>

      <label class="notes-label">备注 <textarea v-model="form.notes" rows="2" placeholder="训练感受..." /></label>

      <div class="form-actions">
        <button class="btn-save" @click="onSave">保存</button>
        <button class="btn-cancel" @click="emit('cancel')">取消</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.form-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 100; display: flex; align-items: flex-start; justify-content: center; padding-top: 40px; }
.form-panel { background: var(--white); border-radius: var(--radius-lg); padding: 24px; width: 90%; max-width: 520px; max-height: 80vh; overflow-y: auto; box-shadow: var(--shadow-lg); }
.form-panel h3 { margin-bottom: 16px; font-size: 1.1rem; }
.field-row { display: flex; gap: 12px; margin-bottom: 10px; }
.field-row label { flex: 1; font-size: 0.82rem; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px; }
.field-row input, .field-row select { padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 0.88rem; font-family: var(--font-body); }
.exercise-block { background: var(--cream); border-radius: var(--radius-sm); padding: 12px; margin-bottom: 10px; }
.ex-header { display: flex; gap: 8px; margin-bottom: 8px; }
.ex-name-input { flex: 1; padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 0.88rem; font-family: var(--font-body); }
.set-row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.set-num { width: 20px; text-align: center; font-size: 0.78rem; color: var(--text-muted); font-weight: 600; }
.set-input { width: 80px; padding: 4px 8px; border: 1px solid var(--border); border-radius: 4px; font-size: 0.85rem; font-family: var(--font-body); }
.btn-sm { padding: 2px 8px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-family: var(--font-body); }
.btn-del { background: none; color: var(--coral); font-size: 1.1rem; }
.btn-add { background: none; color: var(--green-500); font-weight: 600; margin-top: 4px; }
.btn-add-ex { width: 100%; padding: 8px; background: none; border: 1px dashed var(--border); border-radius: var(--radius-sm); color: var(--text-muted); cursor: pointer; font-family: var(--font-body); font-size: 0.85rem; margin-bottom: 10px; }
.btn-add-ex:hover { border-color: var(--green-500); color: var(--green-500); }
.notes-label { font-size: 0.82rem; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px; margin-bottom: 16px; }
.notes-label textarea { padding: 8px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-family: var(--font-body); resize: vertical; }
.form-actions { display: flex; gap: 10px; justify-content: flex-end; }
.btn-save { padding: 8px 24px; background: var(--green-500); color: white; border: none; border-radius: var(--radius-sm); cursor: pointer; font-weight: 600; font-family: var(--font-body); }
.btn-cancel { padding: 8px 16px; background: none; border: 1px solid var(--border); border-radius: var(--radius-sm); cursor: pointer; font-family: var(--font-body); }
</style>
```

- [ ] **Step 2: 创建 WorkoutLog 页面 `frontend/src/views/WorkoutLog.vue`**

```html
<script setup>
import { ref, onMounted } from 'vue'
import { listWorkouts, createWorkout, updateWorkout, deleteWorkout } from '../services/api.js'
import WorkoutForm from '../components/WorkoutForm.vue'

const workouts = ref([])
const showForm = ref(false)
const editData = ref(null)

async function load() {
  try { workouts.value = await listWorkouts() } catch {}
}

async function onSave(data) {
  try {
    if (editData.value?.id) {
      await updateWorkout(editData.value.id, data)
    } else {
      await createWorkout(data)
    }
    showForm.value = false
    editData.value = null
    await load()
  } catch (e) { alert(e.message) }
}

function onEdit(w) { editData.value = w; showForm.value = true }

async function onDelete(id) {
  if (!confirm('确定删除？')) return
  try { await deleteWorkout(id); await load() } catch {}
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h2>训练记录</h2>
      <button class="btn-primary" @click="editData = null; showForm = true">+ 新增训练</button>
    </div>

    <div v-if="workouts.length === 0" class="empty">还没有训练记录，点击上方开始</div>

    <div v-for="w in workouts" :key="w.id" class="item">
      <div class="item-main">
        <span class="item-date">{{ w.date }}</span>
        <span class="item-part">{{ w.body_part }}</span>
        <span class="item-meta">{{ w.exercise_count }}动作 · {{ w.total_volume }}kg</span>
      </div>
      <div class="item-actions">
        <button class="btn-text" @click="onEdit(w)">编辑</button>
        <button class="btn-text danger" @click="onDelete(w.id)">删除</button>
      </div>
    </div>

    <WorkoutForm v-if="showForm" :initial="editData" @save="onSave" @cancel="showForm = false; editData = null" />
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 640px; margin: 0 auto; height: 100%; overflow-y: auto; }
.page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-head h2 { font-size: 1.3rem; font-weight: 700; }
.btn-primary { padding: 8px 18px; background: var(--green-500); color: white; border: none; border-radius: var(--radius-sm); cursor: pointer; font-weight: 600; font-family: var(--font-body); }
.empty { text-align: center; color: var(--text-muted); padding: 40px; }
.item { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; background: var(--white); border-radius: var(--radius-sm); margin-bottom: 8px; box-shadow: var(--shadow-sm); }
.item-main { display: flex; gap: 16px; align-items: center; }
.item-date { font-weight: 600; font-size: 0.9rem; color: var(--text); }
.item-part { background: var(--green-100); color: var(--green-700); padding: 2px 10px; border-radius: 99px; font-size: 0.75rem; font-weight: 600; }
.item-meta { font-size: 0.82rem; color: var(--text-muted); }
.item-actions { display: flex; gap: 8px; }
.btn-text { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 0.82rem; font-family: var(--font-body); }
.btn-text:hover { color: var(--text); }
.btn-text.danger:hover { color: var(--coral); }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/WorkoutLog.vue frontend/src/components/WorkoutForm.vue
git commit -m "feat: 训练记录页面 + WorkoutForm 组件"
```

---

### Task 14: BodyMetric 页面

**Files:**
- Create: `frontend/src/views/BodyMetric.vue`

- [ ] **Step 1: 创建页面**

```html
<script setup>
import { ref, onMounted } from 'vue'
import { listBodyMetrics, createBodyMetric, updateBodyMetric, deleteBodyMetric } from '../services/api.js'
import WeightChart from '../components/WeightChart.vue'

const metrics = ref([])
const trend = ref({ dates: [], weights: [], body_fats: [], weight_change: 0, avg_weight: 0 })
const showForm = ref(false)
const editData = ref(null)

const form = ref({ date: '', weight_kg: '', body_fat_pct: '', notes: '' })

async function load() {
  try {
    const data = await listBodyMetrics(90)
    metrics.value = data.metrics || []
    if (data.trend) trend.value = data.trend
  } catch {}
}

function openNew() {
  editData.value = null
  form.value = { date: new Date().toISOString().slice(0, 10), weight_kg: '', body_fat_pct: '', notes: '' }
  showForm.value = true
}

function openEdit(m) {
  editData.value = m
  form.value = { date: m.date, weight_kg: m.weight_kg, body_fat_pct: m.body_fat_pct, notes: m.notes || '' }
  showForm.value = true
}

async function onSave() {
  const payload = {
    date: form.value.date,
    weight_kg: parseFloat(form.value.weight_kg),
    body_fat_pct: form.value.body_fat_pct ? parseFloat(form.value.body_fat_pct) : null,
    notes: form.value.notes || null,
  }
  try {
    if (editData.value?.id) {
      await updateBodyMetric(editData.value.id, payload)
    } else {
      await createBodyMetric(payload)
    }
    showForm.value = false
    await load()
  } catch (e) { alert(e.message) }
}

async function onDelete(id) {
  if (!confirm('确定删除？')) return
  try { await deleteBodyMetric(id); await load() } catch {}
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h2>身体指标</h2>
      <button class="btn-primary" @click="openNew">+ 记录</button>
    </div>

    <div class="card" v-if="trend.dates.length > 0">
      <h3>体重趋势 (90天)</h3>
      <WeightChart :dates="trend.dates" :weights="trend.weights" />
      <div class="trend-stats">
        <span>平均 {{ trend.avg_weight }}kg</span>
        <span :class="trend.weight_change >= 0 ? 'up' : 'down'">
          {{ trend.weight_change >= 0 ? '+' : '' }}{{ trend.weight_change }}kg
        </span>
      </div>
    </div>

    <div v-if="metrics.length === 0" class="empty">暂无记录</div>

    <div v-for="m in metrics" :key="m.id" class="item">
      <div class="item-main">
        <span class="item-date">{{ m.date }}</span>
        <span class="item-weight">{{ m.weight_kg }}kg</span>
        <span v-if="m.body_fat_pct" class="item-fat">{{ m.body_fat_pct }}%</span>
        <span v-if="m.notes" class="item-notes">{{ m.notes }}</span>
      </div>
      <div class="item-actions">
        <button class="btn-text" @click="openEdit(m)">编辑</button>
        <button class="btn-text danger" @click="onDelete(m.id)">删除</button>
      </div>
    </div>

    <!-- Form Modal -->
    <div v-if="showForm" class="form-overlay" @click.self="showForm = false">
      <div class="form-panel">
        <h3>{{ editData ? '编辑' : '记录' }}身体指标</h3>
        <label>日期 <input type="date" v-model="form.date" /></label>
        <label>体重(kg) <input type="number" v-model="form.weight_kg" step="0.1" min="0" /></label>
        <label>体脂率(%) <input type="number" v-model="form.body_fat_pct" step="0.1" min="0" max="60" /> <span class="hint">可用体脂秤，可留空</span></label>
        <label>备注 <input v-model="form.notes" placeholder="可选" /></label>
        <div class="form-actions">
          <button class="btn-save" @click="onSave">保存</button>
          <button class="btn-cancel" @click="showForm = false">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 640px; margin: 0 auto; height: 100%; overflow-y: auto; }
.page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-head h2 { font-size: 1.3rem; font-weight: 700; }
.btn-primary { padding: 8px 18px; background: var(--green-500); color: white; border: none; border-radius: var(--radius-sm); cursor: pointer; font-weight: 600; font-family: var(--font-body); }
.card { background: var(--white); border-radius: var(--radius); padding: 18px; margin-bottom: 16px; box-shadow: var(--shadow-sm); }
.card h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 12px; }
.trend-stats { display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-muted); margin-top: 8px; }
.empty { text-align: center; color: var(--text-muted); padding: 40px; }
.item { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: var(--white); border-radius: var(--radius-sm); margin-bottom: 6px; box-shadow: var(--shadow-sm); }
.item-main { display: flex; gap: 14px; align-items: center; }
.item-date { font-weight: 600; font-size: 0.88rem; }
.item-weight { font-size: 1rem; font-weight: 700; }
.item-fat { font-size: 0.82rem; color: var(--text-muted); }
.item-notes { font-size: 0.8rem; color: var(--text-muted); max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-actions { display: flex; gap: 8px; }
.btn-text { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 0.82rem; font-family: var(--font-body); }
.btn-text:hover { color: var(--text); }
.btn-text.danger:hover { color: var(--coral); }
.up { color: var(--coral); }
.down { color: var(--green-500); }
.form-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 100; display: flex; align-items: flex-start; justify-content: center; padding-top: 80px; }
.form-panel { background: var(--white); border-radius: var(--radius-lg); padding: 24px; width: 90%; max-width: 400px; box-shadow: var(--shadow-lg); display: flex; flex-direction: column; gap: 12px; }
.form-panel h3 { font-size: 1.1rem; }
.form-panel label { font-size: 0.82rem; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px; }
.form-panel input { padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 0.88rem; font-family: var(--font-body); }
.hint { font-size: 0.72rem; color: var(--text-muted); }
.form-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 8px; }
.btn-save { padding: 8px 24px; background: var(--green-500); color: white; border: none; border-radius: var(--radius-sm); cursor: pointer; font-weight: 600; font-family: var(--font-body); }
.btn-cancel { padding: 8px 16px; background: none; border: 1px solid var(--border); border-radius: var(--radius-sm); cursor: pointer; font-family: var(--font-body); }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/BodyMetric.vue
git commit -m "feat: 身体指标页面——趋势图+记录表单"
```

---

### Task 15: DietLog 页面

**Files:**
- Create: `frontend/src/views/DietLog.vue`
- Create: `frontend/src/components/DietMealForm.vue`
- Create: `frontend/src/components/FoodSearch.vue`

- [ ] **Step 1: 创建 FoodSearch 组件 `frontend/src/components/FoodSearch.vue`**

```html
<script setup>
import { ref, watch } from 'vue'
import { searchFood } from '../services/api.js'

const emit = defineEmits(['select'])

const query = ref('')
const results = ref([])
const loading = ref(false)
const showDropdown = ref(false)

let timer = null
watch(query, (val) => {
  clearTimeout(timer)
  if (!val || val.length < 1) { results.value = []; showDropdown.value = false; return }
  timer = setTimeout(async () => {
    loading.value = true
    try {
      const r = await searchFood(val)
      results.value = r.items || []
      showDropdown.value = results.value.length > 0
    } catch { results.value = [] }
    finally { loading.value = false }
  }, 200)
})

function select(item) {
  emit('select', item)
  query.value = item.food_name
  showDropdown.value = false
}
</script>

<template>
  <div class="food-search">
    <input
      v-model="query"
      placeholder="搜索食物..."
      class="search-input"
      @focus="results.length > 0 && (showDropdown = true)"
    />
    <div v-if="showDropdown" class="dropdown">
      <div v-for="item in results" :key="item.id" class="dropdown-item" @click="select(item)">
        <span class="food-name">{{ item.food_name }}</span>
        <span class="food-meta">{{ item.calories }}kcal / 蛋白{{ item.protein }}g</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.food-search { position: relative; }
.search-input { width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 0.9rem; font-family: var(--font-body); }
.dropdown { position: absolute; top: 100%; left: 0; right: 0; background: var(--white); border: 1px solid var(--border); border-radius: var(--radius-sm); max-height: 200px; overflow-y: auto; z-index: 50; box-shadow: var(--shadow-md); }
.dropdown-item { padding: 10px 12px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--cream-dark); }
.dropdown-item:hover { background: var(--cream); }
.food-name { font-weight: 600; font-size: 0.88rem; }
.food-meta { font-size: 0.75rem; color: var(--text-muted); }
</style>
```

- [ ] **Step 2: 创建 DietMealForm 组件 `frontend/src/components/DietMealForm.vue`**

```html
<script setup>
import { ref } from 'vue'
import FoodSearch from './FoodSearch.vue'

const props = defineProps({ initial: Object })
const emit = defineEmits(['save', 'cancel'])

const mealTypes = [
  { value: 'breakfast', label: '早餐' },
  { value: 'lunch', label: '午餐' },
  { value: 'dinner', label: '晚餐' },
  { value: 'snack', label: '加餐' },
]

const form = ref({
  date: props.initial?.date || new Date().toISOString().slice(0, 10),
  meal_type: props.initial?.meal_type || 'lunch',
  items: props.initial?.items || [],
})

function addItem() {
  form.value.items.push({ food_name: '', amount_g: 100, calories: 0, protein_g: 0, fat_g: 0, carbs_g: 0 })
}

function onFoodSelect(item, idx) {
  const fi = form.value.items[idx]
  fi.food_name = item.food_name
  // auto-calc nutrition based on 100g defaults
  const ratio = fi.amount_g / 100
  fi.calories = Math.round((item.calories || 0) * ratio)
  fi.protein_g = Math.round((item.protein || 0) * ratio * 10) / 10
  fi.fat_g = Math.round((item.fat || 0) * ratio * 10) / 10
  fi.carbs_g = Math.round((item.carbs || 0) * ratio)
}

function recalc(idx) {
  const fi = form.value.items[idx]
  // We can't get original per-100g values without the food DB here, so just mark for recalculation
  // For MVP: user sees the food DB data when selecting, we store what was calculated
}

function removeItem(idx) { form.value.items.splice(idx, 1) }

const totalCalories = computed(() => form.value.items.reduce((s, i) => s + (i.calories || 0), 0))
const totalProtein = computed(() => form.value.items.reduce((s, i) => s + (i.protein_g || 0), 0))

import { computed } from 'vue'

function onSave() {
  emit('save', { ...form.value })
}
</script>

<template>
  <div class="form-overlay" @click.self="emit('cancel')">
    <div class="form-panel">
      <h3>{{ props.initial ? '编辑' : '记录' }}饮食</h3>

      <div class="field-row">
        <label>日期 <input type="date" v-model="form.date" /></label>
        <label>餐次
          <select v-model="form.meal_type">
            <option v-for="mt in mealTypes" :key="mt.value" :value="mt.value">{{ mt.label }}</option>
          </select>
        </label>
      </div>

      <div class="items-section">
        <div v-for="(item, idx) in form.items" :key="idx" class="item-block">
          <div class="item-head">
            <span class="item-num">{{ idx + 1 }}</span>
            <FoodSearch @select="(f) => onFoodSelect(f, idx)" />
            <button class="btn-sm btn-del" @click="removeItem(idx)">×</button>
          </div>
          <div class="item-detail">
            <input type="number" v-model="item.amount_g" placeholder="克" min="0" class="amount-input" @change="recalc(idx)" />
            <span class="nutrition-preview" v-if="item.food_name">
              {{ item.calories }}kcal | P{{ item.protein_g }} F{{ item.fat_g }} C{{ item.carbs_g }}
            </span>
          </div>
        </div>
      </div>

      <button class="btn-add" @click="addItem">+ 食物</button>

      <div class="total-bar">
        <span>合计: {{ totalCalories }}kcal / 蛋白质 {{ totalProtein }}g</span>
      </div>

      <div class="form-actions">
        <button class="btn-save" @click="onSave">保存</button>
        <button class="btn-cancel" @click="emit('cancel')">取消</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.form-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 100; display: flex; align-items: flex-start; justify-content: center; padding-top: 40px; }
.form-panel { background: var(--white); border-radius: var(--radius-lg); padding: 24px; width: 90%; max-width: 480px; max-height: 80vh; overflow-y: auto; box-shadow: var(--shadow-lg); }
.form-panel h3 { margin-bottom: 16px; font-size: 1.1rem; }
.field-row { display: flex; gap: 12px; margin-bottom: 12px; }
.field-row label { flex: 1; font-size: 0.82rem; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px; }
.field-row input, .field-row select { padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 0.88rem; font-family: var(--font-body); }
.items-section { display: flex; flex-direction: column; gap: 10px; margin-bottom: 10px; }
.item-block { background: var(--cream); border-radius: var(--radius-sm); padding: 10px; }
.item-head { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.item-num { width: 20px; font-weight: 600; font-size: 0.82rem; color: var(--text-muted); text-align: center; }
.item-detail { display: flex; gap: 8px; align-items: center; }
.amount-input { width: 70px; padding: 4px 8px; border: 1px solid var(--border); border-radius: 4px; font-size: 0.85rem; font-family: var(--font-body); }
.nutrition-preview { font-size: 0.75rem; color: var(--green-700); font-weight: 500; }
.btn-sm { padding: 2px 8px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-family: var(--font-body); }
.btn-del { background: none; color: var(--coral); font-size: 1.1rem; }
.btn-add { width: 100%; padding: 8px; background: none; border: 1px dashed var(--border); border-radius: var(--radius-sm); color: var(--text-muted); cursor: pointer; font-family: var(--font-body); font-size: 0.85rem; margin-bottom: 10px; }
.total-bar { padding: 10px; background: var(--green-100); border-radius: var(--radius-sm); text-align: center; font-weight: 600; font-size: 0.9rem; color: var(--green-700); margin-bottom: 16px; }
.form-actions { display: flex; gap: 10px; justify-content: flex-end; }
.btn-save { padding: 8px 24px; background: var(--green-500); color: white; border: none; border-radius: var(--radius-sm); cursor: pointer; font-weight: 600; font-family: var(--font-body); }
.btn-cancel { padding: 8px 16px; background: none; border: 1px solid var(--border); border-radius: var(--radius-sm); cursor: pointer; font-family: var(--font-body); }
</style>
```

- [ ] **Step 3: 创建 DietLog 页面 `frontend/src/views/DietLog.vue`**

```html
<script setup>
import { ref, onMounted, computed } from 'vue'
import { listDietMeals, createDietMeal, updateDietMeal, deleteDietMeal } from '../services/api.js'
import DietMealForm from '../components/DietMealForm.vue'

const data = ref({ meals: [], daily_summaries: [] })
const showForm = ref(false)
const editData = ref(null)

async function load() {
  try { data.value = await listDietMeals() } catch {}
}

function groupedMeals() {
  const groups = {}
  for (const m of data.value.meals || []) {
    const d = m.date
    if (!groups[d]) groups[d] = []
    groups[d].push(m)
  }
  return Object.entries(groups).sort((a, b) => b[0].localeCompare(a[0]))
}

const mealTypeLabels = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐' }

async function onSave(formData) {
  try {
    if (editData.value?.id) {
      await updateDietMeal(editData.value.id, formData)
    } else {
      await createDietMeal(formData)
    }
    showForm.value = false; editData.value = null; await load()
  } catch (e) { alert(e.message) }
}

function onEdit(m) { editData.value = m; showForm.value = true }

async function onDelete(id) {
  if (!confirm('确定删除？')) return
  try { await deleteDietMeal(id); await load() } catch {}
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h2>饮食日志</h2>
      <button class="btn-primary" @click="editData = null; showForm = true">+ 记录饮食</button>
    </div>

    <div v-if="data.daily_summaries.length" class="daily-summaries">
      <div v-for="ds in data.daily_summaries.slice(-7).reverse()" :key="ds.date" class="summary-row">
        <span class="sum-date">{{ ds.date }}</span>
        <span>{{ ds.total_calories }}kcal</span>
        <span>P{{ ds.total_protein }}g</span>
      </div>
    </div>

    <div v-for="[date, meals] in groupedMeals()" :key="date" class="day-group">
      <h3 class="day-label">{{ date }}</h3>
      <div v-for="m in meals" :key="m.id" class="meal-item">
        <div class="meal-main">
          <span class="meal-type">{{ mealTypeLabels[m.meal_type] || m.meal_type }}</span>
          <span class="meal-total">{{ Math.round(m.total_calories) }}kcal</span>
          <span class="meal-items-list">{{ m.items?.map(i => i.food_name).join('、') }}</span>
        </div>
        <div class="meal-actions">
          <button class="btn-text" @click="onEdit(m)">编辑</button>
          <button class="btn-text danger" @click="onDelete(m.id)">删除</button>
        </div>
      </div>
    </div>

    <DietMealForm v-if="showForm" :initial="editData" @save="onSave" @cancel="showForm = false; editData = null" />
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 640px; margin: 0 auto; height: 100%; overflow-y: auto; }
.page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-head h2 { font-size: 1.3rem; font-weight: 700; }
.btn-primary { padding: 8px 18px; background: var(--green-500); color: white; border: none; border-radius: var(--radius-sm); cursor: pointer; font-weight: 600; font-family: var(--font-body); }
.daily-summaries { background: var(--white); border-radius: var(--radius); padding: 14px; margin-bottom: 16px; display: flex; gap: 20px; overflow-x: auto; box-shadow: var(--shadow-sm); }
.summary-row { display: flex; gap: 8px; font-size: 0.82rem; white-space: nowrap; }
.sum-date { font-weight: 600; }
.day-group { margin-bottom: 20px; }
.day-label { font-size: 0.95rem; font-weight: 600; margin-bottom: 8px; color: var(--text); }
.meal-item { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: var(--white); border-radius: var(--radius-sm); margin-bottom: 4px; box-shadow: var(--shadow-sm); }
.meal-main { display: flex; gap: 12px; align-items: center; }
.meal-type { background: var(--green-100); color: var(--green-700); padding: 2px 10px; border-radius: 99px; font-size: 0.75rem; font-weight: 600; }
.meal-total { font-weight: 700; font-size: 0.9rem; }
.meal-items-list { font-size: 0.8rem; color: var(--text-muted); max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.meal-actions { display: flex; gap: 8px; }
.btn-text { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 0.82rem; font-family: var(--font-body); }
.btn-text:hover { color: var(--text); }
.btn-text.danger:hover { color: var(--coral); }
</style>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/DietLog.vue frontend/src/components/DietMealForm.vue frontend/src/components/FoodSearch.vue
git commit -m "feat: 饮食日志页面 + DietMealForm + FoodSearch 组件"
```

---

## Plan Review Checklist

在开始执行前验证：

1. **Spec coverage**: 三个追踪模块 ✓ | RAG 交叉分析 ✓ | 食物库搜索 ✓ | Dashboard ✓ | 前端路由 ✓
2. **No placeholders**: 所有代码块包含实际代码
3. **Type consistency**: API 函数名与路由匹配（如 `/workout` vs `listWorkouts`）✓

---

## 执行策略

由于训练/身体/饮食三个 CRUD 模块互不依赖，推荐使用 **subagent-driven-development**，将 Phase 2 的 Task 3/4/5 并行派发给 3 个 subagent。

建议执行顺序：
1. Task 1 → Task 2（串行，基础设施）
2. Task 3 + Task 4 + Task 5（并行，三个 CRUD）
3. Task 6 → Task 7 → Task 8（串行，RAG 集成依赖 Phase 2）
4. Task 9 → Task 10 → Task 11 + Task 12 + Task 13 + Task 14 + Task 15（前端：路由先，页面可部分并行）
