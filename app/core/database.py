#连接MYSQL数据库

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

#设置日志级别为WARNING以上
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo = False,
    pool_pre_ping = False,# 关闭 ping 检测（aiomysql async 兼容性问题）
    pool_size = 5, #连接池大小
    max_overflow = 10 #最大溢出连接数
)


#创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    bind = engine,
    class_ = AsyncSession,
    expire_on_commit= False
)

#创建基类
Base = declarative_base()

#获取数据会话的依赖函数
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit() #会话提交
        except Exception:
            await session.rollback()#会话回滚
            raise
        finally:
            await session.close()#会话关闭




