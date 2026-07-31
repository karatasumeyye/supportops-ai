from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

# database subsystem configuration
engine = create_async_engine(
    settings.database_url,
    # Check pooled connections before use to avoid stale connections.
    pool_pre_ping=True,
)

# create a session factory that will be used to create new database sessions
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    # Keep ORM fields accessible after commit within request scope.
    expire_on_commit=False,
)


# Dependency function to get a database session
async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        yield session
