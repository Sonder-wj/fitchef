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
    """创建训练记录，含动作和组详情"""
    return await workout_service.create(db, current_user.id, data)


@router.get("", response_model=list[WorkoutSummary], summary="训练列表")
async def list_workouts(
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询登录用户的训练记录列表，摘要含训练容量"""
    return await workout_service.list_workouts(
        db, current_user.id, start_date, end_date, limit
    )


@router.get("/exercises", summary="历史动作名列表")
async def get_exercise_names(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户历史所有动作名称，用于前端自动补全"""
    names = await workout_service.get_exercise_names(db, current_user.id)
    return {"exercises": names}


@router.get("/{workout_id}", response_model=WorkoutOut, summary="训练详情")
async def get_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取一条训练记录完整详情（含动作和组）"""
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
    """编辑训练记录，全量替换动作和组"""
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
    """删除一条训练记录，级联删除动作和组"""
    ok = await workout_service.delete(db, current_user.id, workout_id)
    if not ok:
        return {"detail": "未找到"}, 404
    return {"message": "已删除"}
