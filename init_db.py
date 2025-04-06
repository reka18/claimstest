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

# Path to the CSV file loaded when container starts
CSV_FILE_PATH = "./claim_1234.csv"


# Retry logic for database connection
async def wait_for_db_connection():
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


# Initialization of data
async def initialize_data():
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


if __name__ == "__main__":
    asyncio.run(initialize_data())
