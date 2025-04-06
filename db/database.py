from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from config import DATABASE_URL

# Create an asynchronous SQLAlchemy engine using the configured database URL.
# This engine supports non-blocking I/O operations for interacting with the database.
engine = create_async_engine(DATABASE_URL, echo=True)

# Create an async session factory that generates new database sessions.
# `expire_on_commit=False` prevents SQLAlchemy from expiring objects after a commit,
# allowing continued access to committed objects without reloading.
async_session = async_sessionmaker(engine, expire_on_commit=False)

# Base class for all ORM models. Used for declaring SQLAlchemy models with the declarative pattern.
# All model classes should inherit from this `Base` to be recognized by SQLAlchemy.
Base = declarative_base()