"""
normalizer.py

This module provides functions to clean and normalize raw claim data
from CSV or JSON sources. It ensures consistent field names, validated
and formatted values, and computed derived fields like `net_fee`.

Used by both batch loaders (CSV init) and API routes (POST /claims).
"""

import re
import pandas as pd
from datetime import datetime

# Maps inconsistent or messy CSV headers to canonical field names
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

# Expected normalized columns required for downstream processing
REQUIRED_COLUMNS = list(COLUMN_MAP.values())


def normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize DataFrame column names for consistency.

    - Lowercases column names
    - Replaces spaces with underscores
    - Maps known aliases to standardized schema names using COLUMN_MAP

    Args:
        df (pd.DataFrame): Raw DataFrame with original headers.

    Returns:
        pd.DataFrame: DataFrame with standardized column names.
    """
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    df.rename(columns=COLUMN_MAP, inplace=True)
    return df


def normalize_monetary_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and convert monetary columns to floats.

    - Removes currency symbols and commas
    - Replaces missing values with 0.0
    - Ensures all values are numeric

    Args:
        df (pd.DataFrame): DataFrame with stringified monetary values.

    Returns:
        pd.DataFrame: DataFrame with numeric monetary columns.
    """
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
    """
    Normalize and validate field values across the claim dataset.

    - Computes `net_fee`
    - Parses service date
    - Validates procedure codes
    - Validates and sanitizes NPIs
    - Normalizes quadrant and plan group

    Args:
        df (pd.DataFrame): DataFrame with cleaned headers and numeric fields.

    Returns:
        pd.DataFrame: Fully normalized and validated DataFrame.
    """
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
    """
    Clean and validate a 10-digit numeric NPI (provider identifier).

    Args:
        npi (str): Raw NPI value (may include formatting characters).

    Returns:
        str: Cleaned 10-digit numeric NPI.

    Raises:
        ValueError: If the NPI is not exactly 10 digits.
    """
    cleaned = re.sub(r"\D", "", str(npi))
    if len(cleaned) != 10:
        raise ValueError(f"Invalid NPI: {npi}")
    return cleaned


def validate_procedure_code(code: str) -> str:
    """
    Validate the procedure code format.

    Args:
        code (str): Raw submitted procedure code.

    Returns:
        str: Validated and uppercased procedure code.

    Raises:
        ValueError: If the code does not start with 'D'.
    """
    code = code.strip().upper()
    if not code.startswith("D"):
        raise ValueError(f"Invalid procedure code: {code}")
    return code


def check_required_columns(df: pd.DataFrame):
    """
    Ensure all required columns are present after header normalization.

    Args:
        df (pd.DataFrame): DataFrame to check.

    Raises:
        KeyError: If any required columns are missing.
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")


def normalize_claim_dict(data: dict) -> dict:
    """
    Normalize a single claim input represented as a dictionary.

    Wraps the dict in a DataFrame to reuse column-level normalizers.

    Args:
        data (dict): Raw claim input from API.

    Returns:
        dict: Normalized claim ready for model creation or DB insertion.
    """
    df = pd.DataFrame([data])
    df = normalize_monetary_fields(df)
    df = normalize_field_values(df)
    return df.iloc[0].to_dict()