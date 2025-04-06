import os

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select, Column, Integer, String, BigInteger, Numeric, Date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from datetime import date, datetime

DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy setup
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()


# Dependency to provide database sessions
async def get_async_session() -> AsyncSession:
    async with async_session() as session:
        yield session


# Define FastAPI application
app = FastAPI()


# Updated database model
class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    service_date = Column(Date, nullable=False)
    submitted_procedure = Column(String(255), nullable=False)
    quadrant = Column(String(10), nullable=True)
    plan_group = Column(String(50), nullable=False)
    subscriber_id = Column(BigInteger, nullable=False)
    provider_npi = Column(BigInteger, nullable=False)
    provider_fees = Column(Numeric(10, 2), nullable=False)
    allowed_fees = Column(Numeric(10, 2), nullable=False)
    member_coinsurance = Column(Numeric(10, 2), nullable=False)
    member_copay = Column(Numeric(10, 2), nullable=False)
    net_fee = Column(Numeric(10, 2), nullable=False)


# Pydantic model for creating claims
class ClaimCreate(BaseModel):
    service_date: date
    submitted_procedure: str
    quadrant: str
    plan_group: str
    subscriber_id: int
    provider_npi: int
    provider_fees: float
    allowed_fees: float
    member_coinsurance: float
    member_copay: float

    @field_validator("submitted_procedure")
    def validate_submitted_procedure(cls, value):
        if not value.startswith("D"):  # Ensure it starts with "D"
            raise ValueError("Submitted procedure must start with the letter 'D'.")
        return value

    @field_validator("provider_npi")
    def validate_provider_npi(cls, value):
        # Ensure provider_npi is exactly 10 digits
        if not (1000000000 <= value <= 9999999999):
            raise ValueError("Provider NPI must be a valid 10-digit number.")
        return value

    @field_validator("service_date", mode="before")
    def parse_custom_date(cls, value):
        """
        Parse the custom date format ("3/28/18 0:00") into the ISO 8601 date format.
        """
        if isinstance(value, date):  # Already a valid date object
            return value
        try:
            # Parse using the custom format and return in ISO 8601 format
            parsed_date = datetime.strptime(value, "%m/%d/%y %H:%M")
            return parsed_date.date()  # Convert datetime to date object
        except ValueError:
            raise ValueError(
                "service_date must be in the format 'MM/DD/YY HH:MM', e.g., '3/28/18 0:00'"
            )


@app.post("/claims", status_code=status.HTTP_201_CREATED)
async def create_claim(
        claim: ClaimCreate,
        session: AsyncSession = Depends(get_async_session),
):
    net_fee = claim.provider_fees + claim.member_coinsurance + claim.member_copay - claim.allowed_fees
    if net_fee < 0:
        raise HTTPException(status_code=400, detail="Calculated net fee cannot be negative")

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

    session.add(claim_object)
    await session.commit()
    await session.refresh(claim_object)
    return claim_object


@app.get("/claims")
async def get_all_claims(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Claim))  # Leverage ORM
    claims = result.scalars().all()
    return claims


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {"message": "OK"}


@app.get("/top_providers")
async def get_top_providers(session: AsyncSession = Depends(get_async_session)):
    """
    Fetches the top 10 providers by net fees.
    Utilizes database indexing for optimal query performance.
    """
    query = (
        select(Claim.provider_npi, func.sum(Claim.net_fee).label("total_net_fee"))
        .group_by(Claim.provider_npi)  # Leveraging index on provider_npi
        .order_by(func.sum(Claim.net_fee).desc())  # Optimized with index on net_fee
        .limit(10)  # Limit to top 10 providers
    )
    result = await session.execute(query)
    top_providers = result.all()
    return {
        "top_providers": [
            {"provider_npi": row.provider_npi, "total_net_fee": row.total_net_fee}
            for row in top_providers
        ]
    }
