from loguru import logger
import sys
from pathlib import Path

# 创建日志目录， Path 指的是当前工作目录下的 logs 目录
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 移除默认的控制台输出
logger.remove()

# 添加控制台输出
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# 添加文件输出
logger.add(
    "logs/app.log",  # 普通日志文件
    rotation="500 MB",  # 日志文件大小超过500MB时轮转
    retention="10 days",  # 保留10天的日志
    compression="zip",  # 压缩旧的日志文件
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    encoding="utf-8"
)

# 错误日志单独存储
logger.add(
    "logs/error.log",  # 错误日志文件
    rotation="100 MB",
    retention="30 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    encoding="utf-8"
)


def get_logger(service: str):
    """获取带有服务名称的 logger"""
    return logger.bind(service=service)

