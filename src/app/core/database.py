"""数据库工具层"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.app.core.config import settings
from src.app.core.logging import logger


class Base(DeclarativeBase):
    """SQLAlchemy 声明基类"""


class DatabaseService:
    """异步数据库服务"""

    def __init__(self):
        self._engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话上下文管理器"""
        session = self._session_factory()
        try:
            logger.debug("数据库会话已创建")
            yield session
            await session.commit()
            logger.debug("数据库会话已提交")
        except Exception:
            await session.rollback()
            logger.error("数据库会话已回滚", exc_info=True)
            raise
        finally:
            await session.close()
            logger.debug("数据库会话已关闭")

    async def init_db(self) -> None:
        """初始化数据库表"""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("数据库表初始化完成")

    async def close(self) -> None:
        """关闭数据库连接"""
        await self._engine.dispose()
        logger.info("数据库引擎已关闭")


db_service = DatabaseService()
