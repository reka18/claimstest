import pytest
from fastapi.testclient import TestClient
from app.main import app, Base, engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Create an async session factory for database transactions
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


# Fixture to set up and tear down the test database
@pytest.fixture(scope="module")
async def setup_test_database():
    """
    Fixture to set up the database schema before tests
    and tear it down after tests are complete.
    """

    async def _create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _drop_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    # Create database tables before running tests
    await _create_tables()

    yield  # Allow tests to run

    # Drop tables after tests complete
    await _drop_tables()




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

@pytest.mark.asyncio
async def test_create_claim_valid(client):
    """
    Validate that a claim is created successfully and net fee is calculated.
    """
    payload = {
        "provider_npi": "1234567890",
        "submitted_procedure": "D0123",
        "allowed_fees": 100.00,
        "provider_fees": 80.00,
        "member_coinsurance": 10.00,
        "member_copay": 5.00
    }
    response = client.post("/claims/", json=payload)
    assert response.status_code == 200
    created_claim = response.json()
    assert created_claim["net_fee"] == 80 + 10 + 5 - 100  # Validate net_fee calculation