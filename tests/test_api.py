from datetime import datetime

import httpx
import pytest

BASE_URL = "http://0.0.0.0:8001"


@pytest.mark.asyncio
async def test_health_check():
    """
    Test the /health endpoint to confirm service availability.

    Sends a GET request to /health and verifies:
    - HTTP 200 response status
    - JSON body is {"message": "OK"}
    """
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"message": "OK"}


@pytest.mark.asyncio
async def test_get_all_claims():
    """
    Test the /claims endpoint for retrieving all stored claim records.

    Sends a GET request to /claims and checks:
    - HTTP 200 response status
    - Response is a list
    - If claims exist, they contain an 'id' field
    """
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        response = await client.get("/claims")

    assert response.status_code == 200
    claims = response.json()
    assert isinstance(claims, list)

    if claims:
        assert "id" in claims[0]


@pytest.mark.asyncio
async def test_get_top_providers():
    """
    Test the /top_providers endpoint for computing top NPIs by net fee.

    Sends a GET request and validates:
    - HTTP 200 response status
    - JSON structure contains "top_providers" as a list
    - Each provider entry includes "provider_npi"
    - Validates specific values for provider at index 2
    """
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        response = await client.get("/top_providers")

    assert response.status_code == 200
    data = response.json()

    assert "top_providers" in data
    providers = data["top_providers"]
    assert isinstance(providers, list)

    if providers:
        assert "provider_npi" in providers[0]

    # Validates known test data order
    assert providers[2]["provider_npi"] == 1497775530
    assert providers[2]["total_net_fee"] == 116.85


@pytest.mark.asyncio
async def test_create_claim():
    """
    Test the /claims POST endpoint to create a new claim.

    Sends a valid JSON payload and checks:
    - HTTP 201 response status
    - Correct net fee is computed
    - All returned fields match the request input
    """
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
        response = await client.post("/claims", json=new_claim)

    assert response.status_code == 201
    created_claim = response.json()

    new_claim["net_fee"] = 120.5
    for key in new_claim:
        if key == "service_date":
            parsed_date = datetime.strptime(new_claim[key], "%m/%d/%y %H:%M")
            assert parsed_date.date().isoformat() == created_claim[key]
        else:
            assert key in created_claim
            assert created_claim[key] == new_claim[key]


@pytest.mark.asyncio
async def test_top_providers():
    """
    Validate that the /top_providers endpoint returns expected ordering and net fees.

    Compares the API response to a known expected output of top 10 provider NPIs.
    Checks both structure and values.

    Raises:
        AssertionError: If the actual output differs from the expected.
    """
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
        response = await client.get("/top_providers")

    assert response.status_code == 200
    print(response.json())
    assert response.json() == expected_output