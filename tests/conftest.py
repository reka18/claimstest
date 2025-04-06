import os
import subprocess
import time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient
from app.main import app, Base, get_async_session  # Import get_async_session explicitly

# Test-specific database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5433/test_db"

# Create test engine and session
test_engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def start_postgres_container():
    """
    Fixture to start the test Postgres container at the beginning of the test session
    and stop it at the end.
    """
    print("\nStarting Postgres test container...")
    subprocess.run(
        ["docker-compose", "up", "-d"], cwd="tests", check=True
    )
    time.sleep(10)  # Adjust if necessary based on database readiness
    yield
    print("\nStopping Postgres test container...")
    subprocess.run(
        ["docker-compose", "down", "-v"], cwd="tests", check=True
    )


@pytest.fixture(scope="module")
async def setup_test_database():
    """
    Fixture to set up the test database schema before tests
    and drop it afterward.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def override_get_async_session():
    """
    Override the app's `get_async_session` dependency to use the test database.
    """
    async def _override_session():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_async_session] = _override_session
    yield
    app.dependency_overrides.clear()  # Clean up after the fixture


@pytest.fixture
def client(override_get_async_session):
    """
    Fixture for synchronous TestClient to test FastAPI endpoints.
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client(override_get_async_session, setup_test_database):
    """
    Fixture for asynchronous TestClient to test FastAPI endpoints.
    """
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client