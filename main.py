from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, BigInteger, Numeric, Date, TIMESTAMP, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = "postgresql+asyncpg://claim_user:claim_password@db/claims_db"

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
    service_date = Column(Date, nullable=True)  # New column
    submitted_procedure = Column(String(255), nullable=False)
    quadrant = Column(String(10), nullable=True)  # New column
    plan_group = Column(String(50), nullable=False)  # New column
    subscriber_id = Column(BigInteger, nullable=False)  # New column
    provider_npi = Column(BigInteger, nullable=False)
    provider_fees = Column(Numeric(10, 2), nullable=False)
    allowed_fees = Column(Numeric(10, 2), nullable=False)
    member_coinsurance = Column(Numeric(10, 2), nullable=False)
    member_copay = Column(Numeric(10, 2), nullable=False)
    net_fee = Column(Numeric(10, 2), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)  # Matches DB type


# Pydantic model for creating claims
class ClaimCreate(BaseModel):
    provider_npi: str
    submitted_procedure: str
    allowed_fees: float
    provider_fees: float
    member_coinsurance: float
    member_copay: float


@app.post("/claims/")
async def create_claim(claim: ClaimCreate, session: AsyncSession = Depends(get_async_session)):
    net_fee = claim.provider_fees + claim.member_coinsurance + claim.member_copay - claim.allowed_fees
    print(f"Calculated net_fee: {net_fee}")
    new_claim = Claim(**claim.model_dump(), net_fee=net_fee)
    session.add(new_claim)
    await session.commit()
    await session.refresh(new_claim)
    print(f"New claim created: {new_claim}")
    return new_claim


@app.get("/claims/")
async def get_all_claims(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute("SELECT * FROM claims")
    claims = result.fetchall()
    return claims



# Health check endpoint
@app.get("/", tags=["Health"])
async def health_check():
    return {"message": "OK"}
