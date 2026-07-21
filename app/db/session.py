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
    pool_pre_ping=True,   # control the behavior of the connection pool to check if a connection is still valid before using it
)

# create a session factory that will be used to create new database sessions
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevents fields in ORM objects from immediately becoming invalid after a commit
)


# Dependency function to get a database session
async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        yield session