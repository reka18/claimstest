# normalizer.py

import re
import pandas as pd
from datetime import datetime

# Maps messy CSV headers to internal field names
COLUMN_MAP = {
    "service_date": "service_date",
    "submitted_procedure": "submitted_procedure",
    "plan/group_#": "plan_group",
    "subscriber#": "subscriber_id",
    "provider_npi": "provider_npi",
    "provider_fees": "provider_fees",
    "allowed_fees": "allowed_fees",
    "member_coinsurance": "member_coinsurance",
    "member_copay": "member_copay",
    "quadrant": "quadrant"
}

REQUIRED_COLUMNS = list(COLUMN_MAP.values())

def normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    df.rename(columns=COLUMN_MAP, inplace=True)
    return df

def normalize_monetary_fields(df: pd.DataFrame) -> pd.DataFrame:
    monetary_columns = ["provider_fees", "allowed_fees", "member_coinsurance", "member_copay"]
    for col in monetary_columns:
        df[col] = (
            df[col]
            .astype(str)
            .replace({r"\$": "", ",": ""}, regex=True)
            .replace("nan", "0")
            .astype(float)
        )
    return df

def normalize_field_values(df: pd.DataFrame) -> pd.DataFrame:
    df["net_fee"] = (
        df["provider_fees"] + df["member_coinsurance"] + df["member_copay"] - df["allowed_fees"]
    )

    df["service_date"] = pd.to_datetime(
        df["service_date"], format="%m/%d/%y %H:%M", errors="coerce"
    )

    df["submitted_procedure"] = df["submitted_procedure"].astype(str).str.upper()
    df["submitted_procedure"] = df["submitted_procedure"].apply(validate_procedure_code)

    df["provider_npi"] = df["provider_npi"].apply(clean_npi).astype("int64")
    df["subscriber_id"] = df["subscriber_id"].astype("int64")
    df["quadrant"] = df.get("quadrant", "").fillna("").astype(str)
    df["plan_group"] = df["plan_group"].astype(str)

    return df

def clean_npi(npi: str) -> str:
    cleaned = re.sub(r"[^\d]", "", str(npi))
    if len(cleaned) != 10:
        raise ValueError(f"Invalid NPI: {npi}")
    return cleaned

def validate_procedure_code(code: str) -> str:
    code = code.strip().upper()
    if not code.startswith("D"):
        raise ValueError(f"Invalid procedure code: {code}")
    return code

def check_required_columns(df: pd.DataFrame):
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")

def normalize_claim_dict(data: dict) -> dict:
    df = pd.DataFrame([data])
    df = normalize_monetary_fields(df)
    df = normalize_field_values(df)
    return df.iloc[0].to_dict()