import os
import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from main import Claim, Base
import asyncio

# Database connection setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://claim_user:claim_password@db/claims_db")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Path to the CSV file loaded when container starts
CSV_FILE_PATH = "./claim_1234.csv"


# Retry logic for database connection
async def wait_for_db_connection():
    retries = 5  # Number of retries
    for attempt in range(retries):
        try:
            # Attempt to connect to the database
            async with engine.begin() as _:
                print("Database connection established.")
                return
        except Exception as e:
            print(f"Database connection failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(5)  # Wait 5 seconds before retrying
            else:
                # If all retries fail, raise an error
                raise RuntimeError("Failed to connect to the database after several attempts")


# Initialization of data
async def initialize_data():
    # Wait for the database connection before proceeding
    await wait_for_db_connection()

    # Drop and recreate the schema on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Drop table if it exists
        await conn.run_sync(Base.metadata.create_all)  # Recreate table

    # Ensure the data file exists
    if not os.path.exists(CSV_FILE_PATH):
        print(f"CSV file not found at {CSV_FILE_PATH}")
        return

    print(f"Reading data from {CSV_FILE_PATH}...")
    data = pd.read_csv(CSV_FILE_PATH)

    # Clean and normalize column names
    data.columns = [col.strip().lower().replace(" ", "_") for col in data.columns]

    # Rename columns to match database schema
    COLUMN_MAP = {
        "service date": "service_date",
        "submitted procedure": "submitted_procedure",
        "Plan/Group #": "plan_group",
        "Subscriber#": "subscriber_id",
        "Provider NPI": "provider_npi",
        "provider fees": "provider_fees",
        "Allowed fees": "allowed_fees",
        "member coinsurance": "member_coinsurance",
        "member copay": "member_copay",
    }
    data.rename(columns=COLUMN_MAP, inplace=True)

    # Ensure all required columns are present
    required_columns = [
        "service_date", "subscriber_id", "provider_npi", "submitted_procedure",
        "plan_group", "quadrant", "provider_fees", "allowed_fees",
        "member_coinsurance", "member_copay"
    ]
    for col in required_columns:
        if col not in data.columns:
            raise KeyError(f"Required column '{col}' is missing from the CSV")

    # Convert monetary fields to `float` or `NUMERIC`
    data["provider_fees"] = data["provider_fees"].replace({r"\$": "", ",": ""}, regex=True).astype(float)
    data["allowed_fees"] = data["allowed_fees"].replace({r"\$": "", ",": ""}, regex=True).astype(float)
    data["member_coinsurance"] = data["member_coinsurance"].replace({r"\$": "", ",": ""}, regex=True).astype(float)
    data["member_copay"] = data["member_copay"].replace({r"\$": "", ",": ""}, regex=True).astype(float)

    # Calculate `net_fee`
    data["net_fee"] = data["provider_fees"] + data["member_coinsurance"] + data["member_copay"] - data["allowed_fees"]

    # Convert `provider_npi` and `subscriber_id` to `int` (for `BIGINT`)
    data["provider_npi"] = data["provider_npi"].astype("int64")
    data["subscriber_id"] = data["subscriber_id"].astype("int64")

    # Parse `service_date` (if present) into a standard `datetime` format
    data["service_date"] = pd.to_datetime(data["service_date"], errors="coerce")

    # Add missing nullable fields; replace NaN with None
    data["quadrant"] = data["quadrant"].fillna("").astype(str)  # Empty strings for quadrant
    data["plan_group"] = data["plan_group"].astype(str)

    # Insert cleaned data into the database
    async with async_session() as session:
        for _, row in data.iterrows():
            # Add each claim to the database
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
    print(f"{len(data)} rows inserted.")


if __name__ == "__main__":
    asyncio.run(initialize_data())
