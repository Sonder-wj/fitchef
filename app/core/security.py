#JWT认证 

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt  # python-jose：Python 的 JWT 库，用于生成和验证 JWT
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from app.services.user_service import UserService
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

# ── OAuth2 密码流 ──────────────────────────────────────────────────────────
# 💡 OAuth2PasswordBearer 是 FastAPI 内置的认证方案：
#   1. 它会自动从请求头的 Authorization 字段中提取 Bearer token
#      例如：Authorization: Bearer eyJhbGciOi...
#   2. tokenUrl="/token" 告诉 Swagger 文档：登录接口在 /token
#      这样 Swagger 页面会自动显示一个"Authorize"按钮
#   3. 后续把这个实例作为 Depends 参数使用时，FastAPI 会自动取出 token 字符串
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── 生成 JWT Token ────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    生成 JWT 访问令牌

    💡 JWT 的结构（三段式，用 . 分隔）：
       Header.Payload.Signature
       - Header：算法类型（HS256）+ token 类型（JWT）
       - Payload：存放数据（谁发的、什么时候过期）
       - Signature：用密钥对前两段签名，防篡改

    参数：
      data：要存进 token 的数据，如 {"sub": "user@example.com"}
            sub 是 JWT 标准字段，表示"主体"（Subject），通常存用户标识
      expires_delta：过期时间，不传则默认 15 分钟
    """
    to_encode = data.copy()  # 复制一份，避免修改原始 dict

    # 设置过期时间，使用 UTC 时间（避免时区问题）
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)

    # exp 是 JWT 标准字段，表示过期时间（Expiration Time）
    to_encode.update({"exp": expire})

    # 用密钥签名生成最终的 JWT 字符串
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


# ── 获取当前登录用户（依赖注入） ───────────────────────────────────────────
async def get_current_user(
    token: str = Depends(oauth2_scheme),    # 🔑 Depends 自动从请求头提取 Bearer token
    db: AsyncSession = Depends(get_db)       # 🔑 Depends 自动获取数据库会话
):
    """
    从 JWT token 中解析出当前用户。
    这个函数通常作为 FastAPI 路由的 Depends 参数使用，
    例如：async def my_route(user: User = Depends(get_current_user))

    💡 执行流程：
       1. 从请求头取出 Bearer token
       2. 解码 token，验证签名和过期时间
       3. 从 token 的 sub 字段取出用户邮箱
       4. 用邮箱去数据库查用户
       5. 找到 → 返回用户对象（路由可直接用）
       6. 找不到 → 抛出 401 未授权错误
    """
    # 预定义 401 错误（多处复用，避免重复代码）
    # WWW-Authenticate 头告诉浏览器"请带上 Bearer token 再来"
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # ── 第一步：解码 token ──
    try:
        # jwt.decode 会做两件事：
        #  ① 验签：用 SECRET_KEY 验证 token 没被篡改
        #  ② 检查过期：如果 exp 时间已过，直接抛 JWTError
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        # sub = Subject，JWT 标准字段，这里存的是用户邮箱
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception

    except JWTError:
        # token 过期、签名不对、格式错误...统统返回 401
        raise credentials_exception

    # ── 第二步：用邮箱查用户 ──
    user = await UserService.get_user_by_email(db, email)  # 静态方法直接用类名调用，不需要实例化

    if user is None:
        # token 有效但用户不存在（可能被删了）
        raise credentials_exception

    return user 