from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, conint, confloat, constr, field_validator

# Edits to push more validation into Pydantic's compiled internals
class ClaimCreate(BaseModel):
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
        if isinstance(v, date):
            return v
        for fmt in ("%m/%d/%y %H:%M", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(v, fmt).date()
            except ValueError:
                continue
        raise ValueError("Invalid service_date format")