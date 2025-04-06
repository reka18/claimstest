from db.database import async_session
from sqlalchemy.ext.asyncio import AsyncSession

async def get_async_session() -> AsyncSession:
    """
    Dependency that provides a SQLAlchemy asynchronous session.

    This function is used with FastAPI's `Depends()` to inject an `AsyncSession`
    into route handlers. It ensures proper session lifecycle management by:
    - Automatically opening a new session on entry.
    - Closing the session after the route handler completes.

    Yields:
        AsyncSession: A single-use SQLAlchemy async session instance.
    """
    async with async_session() as session:
        yield session