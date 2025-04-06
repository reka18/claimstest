import asyncio
import os

import pandas as pd

from db.database import engine, async_session, Base
from db.models import Claim
from normalize import (
    normalize_headers,
    normalize_monetary_fields,
    normalize_field_values,
    check_required_columns,
)

# Path to the CSV file loaded when the container starts
CSV_FILE_PATH = "./claim_1234.csv"


async def wait_for_db_connection():
    """
    Wait for the database connection to be available with retry logic.

    Tries to connect up to 5 times, sleeping 5 seconds between each attempt.
    If all attempts fail, raises a RuntimeError.

    Raises:
        RuntimeError: If the database connection cannot be established.
    """
    retries = 5
    for attempt in range(retries):
        try:
            async with engine.begin() as _:
                print("[INFO] Database connection established.")
                return
        except Exception as e:
            print(f"[WARNING] Database connection failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(5)
            else:
                raise RuntimeError("[ERROR] Failed to connect to the database after several attempts")


async def initialize_data():
    """
    Load and normalize claim data from a CSV file, then insert it into the database.

    This process:
    - Waits for database availability
    - Drops and recreates the claims table
    - Reads the CSV file containing raw claim data
    - Normalizes headers, monetary fields, and claim field values
    - Validates required columns
    - Calculates `net_fee` for each claim
    - Bulk inserts all records into the database

    If the CSV file is missing, the function will log the error and exit gracefully.
    """
    await wait_for_db_connection()

    async with engine.begin() as conn:
        print("[INFO] Dropping and recreating the schema.")
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    print(f"[INFO] Checking for the presence of CSV file at: {CSV_FILE_PATH}")
    if not os.path.exists(CSV_FILE_PATH):
        print(f"[ERROR] CSV file not found at {CSV_FILE_PATH}")
        return

    print(f"[INFO] Reading data from {CSV_FILE_PATH}...")
    data = pd.read_csv(CSV_FILE_PATH)
    print("[DEBUG] Original CSV Columns:", list(data.columns))

    print("[INFO] Normalizing headers...")
    data = normalize_headers(data)
    print("[DEBUG] Normalized CSV Columns:", list(data.columns))

    print("[INFO] Validating required columns...")
    check_required_columns(data)

    print("[INFO] Normalizing monetary fields...")
    data = normalize_monetary_fields(data)

    print("[INFO] Normalizing and validating row values...")
    data = normalize_field_values(data)

    print("[DEBUG] Sample data after full normalization:")
    print(data.head())

    print("[INFO] Inserting data into the database...")
    async with async_session() as session:
        for _, row in data.iterrows():
            claim = Claim(
                service_date=row["service_date"],
                subscriber_id=row["subscriber_id"],
                provider_npi=row["provider_npi"],
                submitted_procedure=row["submitted_procedure"],
                quadrant=row["quadrant"],
                plan_group=row["plan_group"],
                provider_fees=row["provider_fees"],
                allowed_fees=row["allowed_fees"],
                member_coinsurance=row["member_coinsurance"],
                member_copay=row["member_copay"],
                net_fee=row["net_fee"],
            )
            session.add(claim)
        await session.commit()

    print(f"[INFO] Successfully inserted {len(data)} rows into the database.")


# Pseudo-code for batch ingestion (optional):
# ------------------------------------------
# After inserting each claim:
# - Publish net_fee details to the payments queue (same format as above)
# - Consider bulk publishing after batch commit
# - Optionally flag each record as "payment_sent = False" and update after confirmation
if __name__ == "__main__":
    asyncio.run(initialize_data())