from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, Depends
from sqlalchemy import Column, Integer, String, Float
from pydantic import BaseModel

# Use test credentials (hardcoded DATABASE_URL)
DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5433/test_db"

# SQLAlchemy setup
engine = create_async_engine(DATABASE_URL, echo=True)  # Log all SQL queries for debugging
async_session = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()


# Dependency to provide database sessions
async def get_async_session() -> AsyncSession:
    async with async_session() as session:
        yield session


# Define FastAPI application
app = FastAPI()


# Example database model
class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    provider_npi = Column(String, index=True)
    submitted_procedure = Column(String, index=True)
    allowed_fees = Column(Float)
    provider_fees = Column(Float)
    member_coinsurance = Column(Float)
    member_copay = Column(Float)
    net_fee = Column(Float)
    created_at = Column(String)


# Pydantic model for creating claims
class ClaimCreate(BaseModel):
    provider_npi: str
    submitted_procedure: str
    allowed_fees: float
    provider_fees: float
    member_coinsurance: float
    member_copay: float


# Create a claim (example endpoint)
@app.post("/claims/")
async def create_claim(claim: ClaimCreate, session: AsyncSession = Depends(get_async_session)):
    new_claim = Claim(**claim.model_dump(), net_fee=claim.allowed_fees - claim.provider_fees)
    session.add(new_claim)
    await session.commit()
    await session.refresh(new_claim)
    return new_claim


# Example endpoint to fetch all claims
@app.get("/claims/")
async def get_all_claims(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute("SELECT * FROM claims;")
    claims = result.fetchall()
    return claims


# Health check endpoint
@app.get("/", tags=["Health"])
async def health_check():
    return {"message": "OK"}
