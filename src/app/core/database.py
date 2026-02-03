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
            logger.debug("Database session created")
            yield session
            await session.commit()
            logger.debug("Database session committed")
        except Exception:
            await session.rollback()
            logger.error("Database session rolled back", exc_info=True)
            raise
        finally:
            await session.close()
            logger.debug("Database session closed")

    async def init_db(self) -> None:
        """初始化数据库表"""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized successfully")

    async def close(self) -> None:
        """关闭数据库连接"""
        await self._engine.dispose()
        logger.info("Database engine closed")


db_service = DatabaseService()
