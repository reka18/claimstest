from datetime import datetime

import fakeredis
import httpx
import pytest
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter


@pytest.fixture(autouse=True)
async def mock_fastapi_limiter():
    # Use fakeredis as a mock Redis instance
    fake_redis = fakeredis.FakeRedis()
    await FastAPILimiter.init(fake_redis)


BASE_URL = "http://0.0.0.0:8001"


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Make GET request to /health-check endpoint
        response = await client.get("/health")

    # Assertions
    assert response.status_code == 200
    assert response.json() == {"message": "OK"}


@pytest.mark.asyncio
async def test_get_all_claims():
    """Test retrieving all claims."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Make GET request to fetch all claims
        response = await client.get("/claims")

    # Assertions
    assert response.status_code == 200
    claims = response.json()
    assert isinstance(claims, list)  # Response should be a list
    # Additional Assertion: Ensure there is at least one claim
    if claims:
        assert "id" in claims[0]  # Ensure claim objects have the required fields


@pytest.mark.asyncio
async def test_get_top_providers():
    """Test getting the top providers."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Make GET request to fetch top providers
        response = await client.get("/top_providers")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "top_providers" in data  # Response must include the providers key
    providers = data["top_providers"]
    assert isinstance(providers, list)  # Providers should be a list
    # Additional Assertion: Ensure providers have necessary keys
    if providers:
        assert "provider_npi" in providers[0]
    # Assert that 1497775530 is 3rd in the list
    assert providers[2]["provider_npi"] == 1497775530
    # Assert that 1497775530 net_fee is 116
    assert providers[2]["total_net_fee"] == 116.85


@pytest.mark.asyncio
async def test_create_claim():
    """Test creating a new claim."""
    new_claim = {
        "service_date": "3/28/18 0:00",
        "submitted_procedure": "D123",
        "quadrant": "UR",
        "plan_group": "Group A",
        "subscriber_id": 100001,
        "provider_npi": 1234567890,
        "provider_fees": 500.75,
        "allowed_fees": 450.50,
        "member_coinsurance": 50.25,
        "member_copay": 20.00,
    }

    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Make POST request to create a new claim
        response = await client.post("/claims", json=new_claim)

    # Assertions
    assert response.status_code == 201  # Created
    created_claim = response.json()

    # This is the expected net fee calculation
    new_claim["net_fee"] = 120.5
    for key in new_claim:
        if key == "service_date":
            parsed_date = datetime.strptime(new_claim[key], "%m/%d/%y %H:%M")
            # Convert `parsed_date` to ISO string for comparison
            assert parsed_date.date().isoformat() == created_claim[key]
        else:
            assert key in created_claim  # Ensure all fields are returned
            assert created_claim[key] == new_claim[key]  # Values should match


@pytest.mark.asyncio
async def test_top_providers():
    """Test the /top_providers endpoint and validate the response."""
    expected_output = {
        "top_providers": [
            {"provider_npi": 1234567890, "total_net_fee": 570.5},
            {"provider_npi": 1987654321, "total_net_fee": 271.88},
            {"provider_npi": 1497775530, "total_net_fee": 116.85},
            {"provider_npi": 1432109765, "total_net_fee": 90.0},
            {"provider_npi": 1654321987, "total_net_fee": 85.0},
            {"provider_npi": 1543219876, "total_net_fee": 85.0},
            {"provider_npi": 1876543109, "total_net_fee": 72.5},
            {"provider_npi": 1765431098, "total_net_fee": 72.5},
            {"provider_npi": 1987654310, "total_net_fee": 70.0},
            {"provider_npi": 1218764321, "total_net_fee": 67.5}
        ]
    }

    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Make GET request to the /top_providers endpoint
        response = await client.get("/top_providers")

    # Assertions
    assert response.status_code == 200  # Ensure successful response

    print(response.json())

    assert response.json() == expected_output  # Validate the response matches expected output
