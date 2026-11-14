import logging
from collections.abc import AsyncIterator

from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from ai_code_check.core.config import settings

LOGGER = logging.getLogger(__name__)

# 创建引擎(连接池)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,  # 调试模式下，会打印出所有的 SQL 语句
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 超过连接池大小后，最多可以创建的连接数
    pool_timeout=30,  # 连接池获取连接的超时时间，单位秒
    pool_recycle=60 * 5,  # 连接池连接的最大空闲时间，单位秒
    pool_pre_ping=True,  # 连接池在获取连接时，会先测试连接是否可用
)

# 创建会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后保留已加载的 ORM 属性，供事务结束后的业务逻辑使用。
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """提供当前请求使用的数据库会话，并在请求结束后关闭会话。

    Yields:
        当前请求使用的数据库会话。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except RequestValidationError:
            # 交给全局校验异常处理器，避免日志记录请求中的原始输入。
            raise
        except Exception as exc:
            LOGGER.error(exc, exc_info=True)
            raise
