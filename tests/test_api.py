import pytest
import httpx

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
#
#
# @pytest.mark.asyncio
# async def test_get_top_providers():
#     """Test getting the top providers."""
#     async with httpx.AsyncClient(base_url=BASE_URL) as client:
#         # Make GET request to fetch top providers
#         response = await client.get("/claims/top-providers")
#
#     # Assertions
#     assert response.status_code == 200
#     data = response.json()
#     assert "providers" in data  # Response must include the providers key
#     providers = data["providers"]
#     assert isinstance(providers, list)  # Providers should be a list
#     # Additional Assertion: Ensure providers have necessary keys
#     if providers:
#         assert "provider_npi" in providers[0]
#
#
# @pytest.mark.asyncio
# async def test_create_claim():
#     """Test creating a new claim."""
#     new_claim = {
#         "service_date": "2023-10-25",
#         "submitted_procedure": "Procedure ABC",
#         "quadrant": "UR",
#         "plan_group": "Group A",
#         "subscriber_id": 100001,
#         "provider_npi": 1203004567,
#         "provider_fees": 500.75,
#         "allowed_fees": 450.50,
#         "member_coinsurance": 50.25,
#         "member_copay": 20.00,
#         "net_fee": 380.25
#     }
#
#     async with httpx.AsyncClient(base_url=BASE_URL) as client:
#         # Make POST request to create a new claim
#         response = await client.post("/claims", json=new_claim)
#
#     # Assertions
#     assert response.status_code == 201  # Created
#     created_claim = response.json()
#     for key in new_claim:
#         assert key in created_claim  # Ensure all fields are returned
#         assert created_claim[key] == new_claim[key]  # Values should match
#
#
# @pytest.mark.asyncio
# async def test_get_claim_by_id():
#     """Test retrieving a specific claim by its ID."""
#     claim_id = 1  # Assuming a claim with this ID exists in the test dataset
#
#     async with httpx.AsyncClient(base_url=BASE_URL) as client:
#         # Make GET request to fetch a claim by ID
#         response = await client.get(f"/claims/{claim_id}")
#
#     # Assertions
#     assert response.status_code == 200
#     claim = response.json()
#     assert "id" in claim  # Returned claim must have ID
#     assert claim["id"] == claim_id
#
#
# @pytest.mark.asyncio
# async def test_get_non_existent_claim():
#     """Test trying to retrieve a claim that does not exist."""
#     non_existent_id = 999999
#
#     async with httpx.AsyncClient(base_url=BASE_URL) as client:
#         # Make GET request to fetch a non-existent claim
#         response = await client.get(f"/claims/{non_existent_id}")
#
#     # Assertions
#     assert response.status_code == 404  # Not Found
#     assert response.json() == {"detail": f"Claim with id {non_existent_id} not found"}
