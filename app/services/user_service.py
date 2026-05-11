# 职责：用户相关的业务逻辑（注册、登录验证、查询）
# 路由层只管接收请求，具体怎么操作数据库都在这里

from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user import UserCreate
from app.models.user import User
from sqlalchemy import select
from fastapi import HTTPException, status
from app.core.hashing import hash_password, verify_password
from datetime import datetime
class UserService:

    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        """
        注册新用户
        1. 检查用户名/邮箱是否已存在
        2. 密码加密
        3. 存入数据库
        """
        #检查用户名是否已经存在
        result = await db.execute(select(User).where(User.username == user_data.username))
        if result.scalar_one_or_none():  # 加括号才是调用方法
            raise HTTPException(status_code=400, detail="用户名已存在")

        #检查邮箱是否存在
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():  # 加括号才是调用方法
            raise HTTPException(status_code=400, detail="邮箱已经被注册")
        
        #创建用户对象,密码加密后存储
        db_user = User(
            username = user_data.username,
            email = user_data.email,
            password_hash = hash_password(user_data.password)  # 对密码进行加密
        )

        #将用户数据存储到数据库
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)  # 刷新，获取数据库生成的 id 和 created_at
        return db_user
    
    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
        """
        登录验证
        1. 用邮箱查用户
        2. 验证密码
        3. 更新最后登录时间
        """
        #用邮箱查用户
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        # 用户不存在或密码错误，统一返回同一个错误（防止被猜测用户是否存在）
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误"
            )
        
        # 账户被封禁返回错误
        if not user.is_active:
            raise HTTPException(status_code=400,detail="账号已被禁用")
        

        #更新最后登录时间
        user.last_login = datetime.now()
        await db.commit()
        await db.refresh(user)  #刷新
        return user
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id : int) -> User:
        """根据ID查用户"""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=400, detail="用户不存在")
        return user
    
    @staticmethod
    async def get_user_by_email(db:AsyncSession, user_email : str) -> User:
        """根据邮箱查用户"""
        result = await db.execute(select(User).where(User.email == user_email))
        return result.scalar_one_or_none()
    #底层查询函数只负责查，不负责判断结果对不对，把判断权交给调用方，这样复用性更高。

        

        
