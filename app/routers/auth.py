# 职责：注册、登录、获取当前用户 三个接口
# 路由层只管：接收请求 → 调 service → 返回响应，不写业务逻辑

from fastapi import APIRouter, Depends
from app.schemas.user import UserCreate, UserResponse, Token
from app.services.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import create_access_token, get_current_user
from app.models.user import User

# APIRouter 是 FastAPI 的路由分组工具
# prefix="/auth" 表示这个文件里所有接口都以 /auth 开头
# tags=["认证"] 是 /docs 页面的分组标签

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register",response_model= UserResponse, summary = "用户注册")
async def register(
    user_data: UserCreate, # 前端传来的注册信息
    db: AsyncSession = Depends(get_db) # 自动注入数据库会话
):
    """注册新用户,返回用户信息(不含密码)"""

    user = await UserService.create_user(db,user_data)
    return user

@router.post("/login",response_model=Token,summary="用户登录")
async def login(
    # OAuth2PasswordRequestForm 是 FastAPI 内置的表单格式
    # 自动从请求里取 username 和 password 字段
    # 注意：这里 username 字段我们用来传邮箱（前端配合）
    form_data:OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    登录接口，返回 JWT Token
    前端拿到 Token 后，后续请求放在请求头：Authorization: Bearer <token>
    """
    # form_data.username 实际上传的是邮箱
    user = await UserService.authenticate_user(db,form_data.username,form_data.password)
    # 生成 Token，sub 字段存用户名（后续验证 Token 时用来查用户）
    token = create_access_token({"sub": user.email})  # 存邮箱，和 get_current_user 保持一致
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me",response_model=UserResponse,summary="获取当前用户")
async def get_me(
    # Depends(get_current_user) 自动验证 Token 并返回当前用户
    # 如果 Token 无效或过期，自动返回 401，不会进入函数体
    current_user: User = Depends(get_current_user)
):
    """获取当前登录用户的信息（需要登录）"""
    return current_user


