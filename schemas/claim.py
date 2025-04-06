from datetime import date, datetime
from pydantic import BaseModel, field_validator

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
    def validate_procedure(cls, v):
        if not v.startswith("D"):
            raise ValueError("Must start with 'D'")
        return v

    @field_validator("provider_npi")
    def validate_npi(cls, v):
        if not (1000000000 <= v <= 9999999999):
            raise ValueError("Must be 10-digit NPI")
        return v

    @field_validator("service_date", mode="before")
    def parse_service_date(cls, v):
        if isinstance(v, date): return v
        try:
            return datetime.strptime(v, "%m/%d/%y %H:%M").date()
        except ValueError:
            raise ValueError("service_date must be in 'MM/DD/YY HH:MM' format")