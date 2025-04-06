from sqlalchemy import Column, Integer, String, BigInteger, Numeric, Date

from db.database import Base


class Claim(Base):
    """
    ORM model representing a single claim record in the 'claims' table.

    This table stores detailed claim line information including provider charges,
    member contributions, allowed amounts, and calculated net fees for downstream
    consumption (e.g., payments processing or analytics).

    Attributes:
        id (int): Primary key for the claim record.
        service_date (date): The date the service was provided.
        submitted_procedure (str): The procedure code submitted (must start with 'D').
        quadrant (str, optional): The quadrant of the mouth where the procedure occurred (if applicable).
        plan_group (str): Insurance plan or group identifier.
        subscriber_id (int): The subscriber’s unique identifier.
        provider_npi (int): National Provider Identifier (10-digit numeric).
        provider_fees (Decimal): The fee charged by the provider.
        allowed_fees (Decimal): The fee amount approved or reimbursed by the plan.
        member_coinsurance (Decimal): The coinsurance amount paid by the member.
        member_copay (Decimal): The copay amount paid by the member.
        net_fee (Decimal): Calculated fee = provider_fees + coinsurance + copay - allowed_fees.
    """

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