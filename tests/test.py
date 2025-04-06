import pytest
from app.main import app  # Import app for reference if needed

pytest_plugins = ['pytest_asyncio']


def test_health_check(client):  # Use client from conftest.py
    """
    Test a simple health check endpoint to verify the test setup works.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "OK"}


@pytest.mark.asyncio
async def test_create_claim_valid(async_client):  # Use async_client from conftest.py
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

    response = await async_client.post("/claims/", json=payload)
    assert response.status_code == 200
    created_claim = response.json()
    assert created_claim["net_fee"] == -5  # 80 + 10 + 5 - 100 = -5