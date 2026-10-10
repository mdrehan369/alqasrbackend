from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# 1. Replace with your actual DB credentials (or load from environment variables)
# Format: postgresql+asyncpg://user:password@host:port/dbname
DATABASE_URL = "postgresql+asyncpg://postgres:pass1234@localhost:5432/al_qasr_db"

# 2. Create the Async Engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Logs generated SQL statements to the terminal (useful for debugging)
    pool_size=10,  # Keeps a pool of 10 connections alive
    max_overflow=20,
)

# 3. Create the Session Factory
SessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Crucial for async apps to avoid unexpected background fetches
)


# 4. Dependency Injection for FastAPI endpoints
async def get_db() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
