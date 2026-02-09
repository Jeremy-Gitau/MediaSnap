"""Database engine and session management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker

from mediasnap.models.schema import Base
from mediasnap.utils.config import DB_URL
from mediasnap.utils.logging import get_logger

logger = get_logger(__name__)


# Synchronous engine for initial setup
sync_engine = create_engine(
    DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},  # Required for SQLite
)

# Async engine for application use
# SQLite async requires aiosqlite
async_db_url = DB_URL.replace("sqlite://", "sqlite+aiosqlite://")
async_engine = create_async_engine(
    async_db_url,
    echo=False,
    connect_args={"check_same_thread": False},
)

# Session factories
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    This should be called once at application startup.
    """
    logger.info(f"Initializing database at: {DB_URL}")
    
    # Enable foreign keys for SQLite
    @event.listens_for(sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Create all tables
    Base.metadata.create_all(bind=sync_engine)
    logger.info("Database initialized successfully")


def get_sync_session() -> Session:
    """
    Get a synchronous database session.
    
    Returns:
        SQLAlchemy Session instance
    """
    return SyncSessionLocal()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session as a context manager.
    
    Usage:
        async with get_async_session() as session:
            # Use session
            await session.execute(...)
    
    Yields:
        SQLAlchemy AsyncSession instance
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def close_db() -> None:
    """Clean up database connections."""
    await async_engine.dispose()
    logger.info("Database connections closed")
