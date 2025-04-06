from sqlalchemy import Column, Integer, String, BigInteger, Numeric, Date

from db.database import Base


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
