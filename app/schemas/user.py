# schemas/user.py
# 职责：定义接口的数据格式（接收什么、返回什么）
# 注意区分：models/ 是数据库表结构，schemas/ 是接口数据格式

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

#==========================注册===========================
class UserCreate(BaseModel):
    """注册接口,前端需要传这三个字段"""
    username: str = Field(min_length = 3, max_length= 20, description="用户名为3-20个字母之间")
    email: EmailStr = Field(description="邮箱")
    password: str = Field(min_length=6,description="密码最小为6位")



#===========================登录==========================
class UserLogin(BaseModel):
    """登录接口,用邮箱和密码登录"""
    email: str 
    password: str


#===========================响应============================
class UserResponse(BaseModel):
    """返回给前端的用户信息,不含密码"""
    id: int
    username: str
    email: EmailStr
    status: str
    created_at: datetime # 用户注册的时间
    last_login: Optional[datetime] = None #用户最后登录的时间:第一次登录的时候为空
    # Optional表示可以为空 Optional[datetime] = None 表示为 datatime | None
    
    #ORM 的意思是对象关系映射（Object Relational Mapping）——把数据库的"行"映射成 Python 的"对象"，让你不用写 SQL，直接用 Python 操作数据库
    class Config:
        from_attributes = True  # 允许从 SQLAlchemy 对象直接转换成这个 Schema

class Token(BaseModel):
    """登录成功后返回的token"""
    access_token: str
    token_type: str = "bearer" # 固定值，告诉前端用 Bearer 方式携带 Token

class TokenData(BaseModel):
    """token解码后的数据 (内部使用)"""
    username: Optional[str] = None