# Standard Python libraries for date handling
import os
from contextlib import asynccontextmanager
from datetime import date, datetime

import redis.asyncio as redis
# Import FastAPI and its dependencies for building a RESTful API
from fastapi import FastAPI, Depends, status
from fastapi.exceptions import HTTPException
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
# Pydantic for data validation and serialization
from pydantic import BaseModel, field_validator
# SQLAlchemy for async database operations and ORM
from sqlalchemy import select, Column, Integer, String, BigInteger, Numeric, Date
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

# Fetch the database URL from environment variables for security and configurability
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

# --- SQLAlchemy Setup ---
# Create an async engine for PostgreSQL with echo=True for debugging SQL queries
engine = create_async_engine(DATABASE_URL, echo=True)
# Set up an async session factory; expire_on_commit=False keeps objects alive after commit
async_session = async_sessionmaker(engine, expire_on_commit=False)
# Base class for declarative ORM models
Base = declarative_base()


# --- Dependency Injection for DB Sessions ---
# Define a dependency to provide an async database session for each request
# This ensures proper session management (open, yield, close) per request
async def get_async_session() -> AsyncSession:
    async with async_session() as session:
        yield session  # Yield the session to the caller, auto-closed after use

async def startup_event():
    redis_instance = redis.from_url(REDIS_URL, decode_responses=True)  # ✅
    await FastAPILimiter.init(redis_instance)


# --- FastAPI Application ---
# Instantiate the FastAPI app, which will handle all HTTP endpoints
app = FastAPI(on_startup=[startup_event])


# --- Database Model ---
# Define the 'claims' table structure using SQLAlchemy ORM
class Claim(Base):
    __tablename__ = "claims"  # Table name in the database

    # Primary key, auto-incrementing integer with an index for faster lookups
    id = Column(Integer, primary_key=True, index=True)
    # Date of service, required field
    service_date = Column(Date, nullable=False)
    # Procedure code (e.g., "D1234"), limited to 255 chars, required
    submitted_procedure = Column(String(255), nullable=False)
    # Quadrant of the mouth (e.g., "UR"), optional, max 10 chars
    quadrant = Column(String(10), nullable=True)
    # Insurance plan group identifier, required, max 50 chars
    plan_group = Column(String(50), nullable=False)
    # Subscriber ID, a large integer, required
    subscriber_id = Column(BigInteger, nullable=False)
    # National Provider Identifier, a 10-digit integer, required
    provider_npi = Column(BigInteger, nullable=False)
    # Fees charged by the provider, decimal with 10 digits total, 2 after decimal, required
    provider_fees = Column(Numeric(10, 2), nullable=False)
    # Fees allowed by the insurance plan, same precision, required
    allowed_fees = Column(Numeric(10, 2), nullable=False)
    # Member’s coinsurance amount, same precision, required
    member_coinsurance = Column(Numeric(10, 2), nullable=False)
    # Member’s copay amount, same precision, required
    member_copay = Column(Numeric(10, 2), nullable=False)
    # Calculated net fee, same precision, required
    net_fee = Column(Numeric(10, 2), nullable=False)


# --- Pydantic Model for Input Validation ---
# Define a Pydantic model for creating claims, ensuring data is validated before DB insertion
class ClaimCreate(BaseModel):
    service_date: date  # Date of service
    submitted_procedure: str  # Procedure code
    quadrant: str  # Mouth quadrant
    plan_group: str  # Insurance plan group
    subscriber_id: int  # Subscriber ID
    provider_npi: int  # Provider NPI
    provider_fees: float  # Provider’s fees
    allowed_fees: float  # Allowed fees
    member_coinsurance: float  # Coinsurance amount
    member_copay: float  # Copay amount

    # Validate that submitted_procedure starts with "D" (e.g., dental codes)
    @field_validator("submitted_procedure")
    def validate_submitted_procedure(cls, value):
        if not value.startswith("D"):
            raise ValueError("Submitted procedure must start with the letter 'D'.")
        return value

    # Validate provider_npi is a 10-digit number
    @field_validator("provider_npi")
    def validate_provider_npi(cls, value):
        if not (1000000000 <= value <= 9999999999):
            raise ValueError("Provider NPI must be a valid 10-digit number.")
        return value

    # Custom date parser to handle "MM/DD/YY HH:MM" format (e.g., "3/28/18 0:00")
    @field_validator("service_date", mode="before")
    def parse_custom_date(cls, value):
        """
        Convert a custom date string into a proper date object.
        Handles cases where the input might already be a date or needs parsing.
        """
        if isinstance(value, date):  # If already a date, no parsing needed
            return value
        try:
            # Parse the string and extract just the date portion
            parsed_date = datetime.strptime(value, "%m/%d/%y %H:%M")
            return parsed_date.date()
        except ValueError:
            raise ValueError(
                "service_date must be in the format 'MM/DD/YY HH:MM', e.g., '3/28/18 0:00'"
            )


# --- API Endpoints ---
# POST endpoint to create a new claim
@app.post("/claims", status_code=status.HTTP_201_CREATED)
async def create_claim(
        claim: ClaimCreate,  # Incoming claim data, validated by Pydantic
        session: AsyncSession = Depends(get_async_session),  # DB session dependency
):
    # Calculate net_fee based on provided values
    # Formula: provider_fees + member_coinsurance + member_copay - allowed_fees
    net_fee = claim.provider_fees + claim.member_coinsurance + claim.member_copay - claim.allowed_fees
    if net_fee < 0:
        # Prevent negative net fees, which would indicate an invalid financial state
        raise HTTPException(status_code=400, detail="Calculated net fee cannot be negative")

    # Create a new Claim object with all required fields
    claim_object = Claim(
        service_date=claim.service_date,
        submitted_procedure=claim.submitted_procedure,
        quadrant=claim.quadrant,
        plan_group=claim.plan_group,
        subscriber_id=claim.subscriber_id,
        provider_npi=claim.provider_npi,
        provider_fees=claim.provider_fees,
        allowed_fees=claim.allowed_fees,
        member_coinsurance=claim.member_coinsurance,
        member_copay=claim.member_copay,
        net_fee=net_fee,
    )

    # Add the claim to the session, commit it to the DB, and refresh to get the ID
    session.add(claim_object)
    await session.commit()
    await session.refresh(claim_object)
    return claim_object  # Return the created claim with its DB-generated ID


# GET endpoint to fetch all claims
@app.get("/claims", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def get_all_claims(session: AsyncSession = Depends(get_async_session)):
    # Execute a SELECT query using SQLAlchemy ORM to fetch all claims
    result = await session.execute(select(Claim))
    claims = result.scalars().all()  # Extract all claim objects from the result
    return claims  # Return as JSON list


# Health check endpoint for monitoring
@app.get("/health", tags=["Health"])
async def health_check():
    # Simple endpoint to verify the API is running
    return {"message": "OK"}


# GET endpoint to fetch top 10 providers by net fees
@app.get("/top_providers")
async def get_top_providers(session: AsyncSession = Depends(get_async_session)):
    """
    Retrieve the top 10 providers based on total net fees.
    Ties in net fees are broken by sorting provider_npi in descending order.
    """
    # Build a query to sum net fees by provider, group by NPI, and sort
    query = (
        select(Claim.provider_npi, func.sum(Claim.net_fee).label("total_net_fee"))
        .group_by(Claim.provider_npi)  # Aggregate by provider
        .order_by(
            func.sum(Claim.net_fee).desc(),  # Primary sort: highest net fees first
            Claim.provider_npi.desc()  # Secondary sort: highest NPI if tied
        )
        .limit(10)  # Restrict to top 10
    )
    result = await session.execute(query)
    top_providers = result.all()  # Fetch all rows

    # Format the response as a list of dictionaries, converting Numeric to float
    return {
        "top_providers": [
            {"provider_npi": row.provider_npi, "total_net_fee": float(row.total_net_fee)}
            for row in top_providers
        ]
    }


# --- Rate Limiting Setup (Commented Out) ---
@asynccontextmanager
async def lifespan(app):
    redis_instance = None  # Variable to manage Redis connection
    try:
        # Initialize a connection to Redis
        redis_instance = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

        # Test Redis connectivity
        await redis_instance.ping()
        print("Connected to Redis at:", REDIS_URL)

        # Initialize the FastAPI limiter
        await FastAPILimiter.init(redis_instance)
        print("FastAPILimiter initialized successfully!")

        # Yield to boot up the application
        yield
    except Exception as e:
        # Log Redis/FastAPILimiter errors, continue app without rate limiting
        print(f"Error during FastAPILimiter or Redis initialization: {str(e)}")
        yield  # Allow the app to start, even if there's an error
    finally:
        # Cleanup Redis connection when the app shuts down
        if redis_instance:
            await redis_instance.close()


# --- External Payments Service Interaction ---
"""
How External Payments Service Would Query claim_process

The external payments service can interact with `claim_process` through the provided API endpoints. 
Here’s a step-by-step explanation:

1. **Use Case: Query for Claims**
   - The payments service can retrieve claims data from the `claim_process` service, e.g., to fetch claims based on payment status or to get the top 10 providers by net fees generated.
   - Example: GET request to `/claims` or `/top_providers`.

2. **Steps for Query Interaction**:
   a. Payments service sends an HTTP GET request to:
        - `/claims`: To fetch all claims processed by `claim_process`.
        - `/top_providers`: To fetch the top 10 providers by net fees.
   b. The `claim_process` service responds with the requested data in JSON format:
        - If querying `/claims`, it will return the list of all claims.
        - If querying `/top_providers`, it will return a ranked list of provider NPIs and their net fees.

3. **Endpoints Exposed:**
   - `/claims`: Returns all claim details.
   - `/top_providers`: Optimized to return top 10 providers by net fees (rate-limited to prevent overuse).

4. **Retry Mechanism in Case of Failures:**
   - If the claim_process service is unavailable (e.g., network timeout or 500 error):
        - Payments service attempts retries using exponential backoff with a maximum number of attempts (e.g., 3 retries).
        - After retries, log the error and raise an alert to notify the operations team.

5. **Concurrency Handling:**
   - Multiple instances of `claim_process` and `payments` services might run concurrently.
        - Use unique claim IDs to ensure idempotency (claims are processed only once).
        - Proper database transaction isolation levels (e.g., `SERIALIZABLE` or `REPEATABLE READ`) in `claim_process` ensure no duplicate operations are performed on claims during concurrent requests.

6. **Error Handling Framework:**
   - Validation:
        - The payments service validates the contract of the `/claims` response (e.g., required fields like `net_fee` must exist and be a float).
        - If validation fails, log the error and notify the relevant team for fixing the implementation or contract mismatch.
   - Database Errors:
        - If the payments service finds duplicate or corrupt claim data, it raises an error and rejects processing until the issue is resolved.

7. **Example Workflow**:
    - The payments service requests all claims to compute summaries:
        a. Send GET `/claims`.
        b. For each claim, calculate the total payable amount based on `net_fee` retrieved from `claim_process`.
        c. Send results back to the downstream billing system.

    - If payments depend on provider performance:
        a. Query the top 10 providers via `/top_providers`.
        b. Process payouts to the top providers based on `net_fee`.

8. **API Rate Limiting Example**:
   - The `/top_providers` endpoint has a rate limit of 10 requests per minute (if enabled).
   - If the rate limit is exceeded, the payments service should wait for the next window to issue the request to prevent throttling.
"""
