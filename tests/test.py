import pytest
from fastapi.testclient import TestClient
from app.main import app, Base, engine


# Fixture to set up and tear down the test database
@pytest.fixture(autouse=True, scope="module")
def setup_test_database():
    """
    Fixture to set up the database schema before tests
    and tear it down after tests are complete.
    """
    import asyncio

    async def _create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _drop_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    # Run setup
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_create_tables())
    yield
    # Run teardown
    loop.run_until_complete(_drop_tables())


# Fixture for using the TestClient
@pytest.fixture
def client():
    """
    Fixture to create a synchronous TestClient for testing FastAPI.
    """
    with TestClient(app) as test_client:
        yield test_client


# Simple test to check fixtures and app responses
def test_health_check(client):
    """
    Test a simple health check endpoint to verify the test setup works.
    """
    # Act: Make a GET request to the root path ("/")
    response = client.get("/")

    # Assert: Expect a 200 status code and a simple response
    assert response.status_code == 200
    assert response.json() == {"message": "OK"}
