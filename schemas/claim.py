from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, conint, confloat, constr, field_validator

class ClaimCreate(BaseModel):
    """
    Pydantic schema for validating and parsing incoming claim creation data.

    This model ensures all required claim fields are present, formatted correctly,
    and within valid ranges. It pushes most validation into Pydantic's internal
    compilation layer using type constraints (e.g., `conint`, `confloat`, `constr`)
    for better performance and consistency.

    Attributes:
        service_date (date): Date when the service was provided. Parsed from multiple formats.
        submitted_procedure (str): Must start with 'D' (e.g., dental procedure codes).
        quadrant (Optional[str]): Optional anatomical quadrant for the procedure.
        plan_group (str): Insurance plan or group name.
        subscriber_id (int): Unique identifier for the insurance subscriber.
        provider_npi (int): 10-digit National Provider Identifier (NPI).
        provider_fees (float): Fee charged by the provider (non-negative).
        allowed_fees (float): Fee amount allowed by insurance (non-negative).
        member_coinsurance (float): Coinsurance paid by member (non-negative).
        member_copay (float): Copay paid by member (non-negative).
    """

    service_date: date
    submitted_procedure: constr(pattern=r"^D\w+")
    quadrant: Optional[str]
    plan_group: str
    subscriber_id: int
    provider_npi: conint(ge=1000000000, le=9999999999)
    provider_fees: confloat(ge=0)
    allowed_fees: confloat(ge=0)
    member_coinsurance: confloat(ge=0)
    member_copay: confloat(ge=0)

    @field_validator("service_date", mode="before")
    def parse_service_date(cls, v):
        """
        Validator to handle various common input formats for service_date.

        Acceptable formats include:
            - 'MM/DD/YY HH:MM'
            - 'YYYY-MM-DD'
            - 'MM/DD/YYYY'

        Parameters:
            v (str | date): The input value to be parsed as a date.

        Returns:
            date: A valid `date` object parsed from the string input.

        Raises:
            ValueError: If the input format does not match any accepted pattern.
        """
        if isinstance(v, date):
            return v
        for fmt in ("%m/%d/%y %H:%M", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(v, fmt).date()
            except ValueError:
                continue
        raise ValueError("Invalid service_date format")