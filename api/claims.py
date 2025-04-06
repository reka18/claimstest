from fastapi import APIRouter, Depends, status, HTTPException
from fastapi_limiter.depends import RateLimiter
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Claim
from db.normalize import normalize_claim_dict
from dependencies.session import get_async_session
from schemas.claim import ClaimCreate

router = APIRouter()


@router.post("/claims", status_code=status.HTTP_201_CREATED)
async def create_claim(claim: ClaimCreate, session: AsyncSession = Depends(get_async_session)):
    """
    Create a new claim entry in the database after normalizing input fields.

    This endpoint accepts a ClaimCreate payload, normalizes and validates its fields,
    calculates the `net_fee`, and inserts the result into the database.

    Parameters:
        claim (ClaimCreate): The claim submission payload.
        session (AsyncSession): The database session injected by FastAPI dependency.

    Returns:
        Claim: The successfully created Claim record with all normalized fields.

    Raises:
        HTTPException 400: If normalization fails, required fields are invalid,
                           or the resulting net fee is negative.


    # Send net fee to payments service
    # ----------------------------------------------
    # After this claim is persisted successfully,
    # we must notify the payments service that a new claim was processed.

    # Option 1: Asynchronous Message Queue (Recommended for scale and resilience)
    # - Push a message to a Redis stream / Kafka topic / RabbitMQ queue:
    #     payload = {
    #         "claim_id": db_claim.id,
    #         "provider_npi": db_claim.provider_npi,
    #         "net_fee": db_claim.net_fee,
    #         "timestamp": db_claim.service_date.isoformat()
    #     }
    #     queue.publish("claims.to.payments", payload)
    #
    # - The payments service consumes this queue in parallel (multiple instances allowed)
    #
    # - If publishing fails, use retry logic or store a "pending_payment" log for reprocessing

    # Option 2: Direct HTTP Call (Simpler but riskier under load or failure)
    # - response = httpx.post("http://payments-service/handle_claim", json=payload)
    # - If response fails:
    #     - Store failed claim ID in a retry table or log for a background worker to retry
    #     - Mark payment_status = "failed", to be retried via cron or task scheduler

    # Failure Strategy:
    # -----------------
    # - If DB insert fails → no queue push (transaction rolled back)
    # - If queue push fails → retry w/ exponential backoff, DLQ (dead-letter queue), or flag for manual intervention
    # - Ensure idempotency: payments service must handle duplicates safely (deduplicate by claim ID or checksum)
    """
    try:
        cleaned = normalize_claim_dict(claim.model_dump())

        if cleaned["net_fee"] < 0:
            raise HTTPException(400, "Net fee cannot be negative")

        db_claim = Claim(**cleaned)
        session.add(db_claim)
        await session.commit()
        await session.refresh(db_claim)
        return db_claim

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/claims", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def get_all_claims(session: AsyncSession = Depends(get_async_session)):
    """
    Retrieve all claims stored in the database.

    This endpoint returns a list of all claim records without any filtering or pagination.
    A rate limiter is applied to restrict excessive usage.

    Parameters:
        session (AsyncSession): The database session injected by FastAPI dependency.

    Returns:
        List[Claim]: A list of all claim records in the database.
    """
    result = await session.execute(select(Claim))
    return result.scalars().all()


@router.get("/top_providers")
async def get_top_providers(session: AsyncSession = Depends(get_async_session)):
    """
    Retrieve the top 10 provider NPIs by total net fee.

    This endpoint aggregates all claims by `provider_npi`, sums their `net_fee`,
    and returns the top 10 providers with the highest total net fees.
    If multiple providers have the same total net fee, the higher NPI is ranked first.

    Parameters:
        session (AsyncSession): The database session injected by FastAPI dependency.

    Returns:
        dict: A dictionary containing a list of top providers and their total net fees:
              {
                  "top_providers": [
                      {"provider_npi": <int>, "total_net_fee": <float>},
                      ...
                  ]
              }
    """
    query = (
        select(Claim.provider_npi, func.sum(Claim.net_fee).label("total_net_fee"))
        .group_by(Claim.provider_npi)
        .order_by(func.sum(Claim.net_fee).desc(), Claim.provider_npi.desc())
        .limit(10)
    )
    result = await session.execute(query)
    return {
        "top_providers": [
            {"provider_npi": r.provider_npi, "total_net_fee": float(r.total_net_fee)}
            for r in result
        ]
    }