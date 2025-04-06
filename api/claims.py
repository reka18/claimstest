from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi_limiter.depends import RateLimiter

from db.models import Claim
from schemas.claim import ClaimCreate
from dependencies.session import get_async_session

router = APIRouter()

@router.post("/claims", status_code=status.HTTP_201_CREATED)
async def create_claim(claim: ClaimCreate, session: AsyncSession = Depends(get_async_session)):
    net_fee = claim.provider_fees + claim.member_coinsurance + claim.member_copay - claim.allowed_fees
    if net_fee < 0:
        raise HTTPException(400, "Net fee cannot be negative")
    db_claim = Claim(**claim.model_dump(), net_fee=net_fee)
    session.add(db_claim)
    await session.commit()
    await session.refresh(db_claim)
    return db_claim

@router.get("/claims", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def get_all_claims(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Claim))
    return result.scalars().all()

@router.get("/top_providers")
async def get_top_providers(session: AsyncSession = Depends(get_async_session)):
    query = (
        select(Claim.provider_npi, func.sum(Claim.net_fee).label("total_net_fee"))
        .group_by(Claim.provider_npi)
        .order_by(func.sum(Claim.net_fee).desc(), Claim.provider_npi.desc())
        .limit(10)
    )
    result = await session.execute(query)
    return {"top_providers": [{"provider_npi": r.provider_npi, "total_net_fee": float(r.total_net_fee)} for r in result]}