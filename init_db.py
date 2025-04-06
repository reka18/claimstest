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
                print("[INFO] Database connection established.")
                return
        except Exception as e:
            print(f"[WARNING] Database connection failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(5)  # Wait 5 seconds before retrying
            else:
                # If all retries fail, raise an error
                raise RuntimeError("[ERROR] Failed to connect to the database after several attempts")


# Initialization of data
async def initialize_data():
    # Wait for the database connection before proceeding
    await wait_for_db_connection()

    # Drop and recreate the schema on startup
    async with engine.begin() as conn:
        print("[INFO] Dropping and recreating the schema.")
        await conn.run_sync(Base.metadata.drop_all)  # Drop table if it exists
        await conn.run_sync(Base.metadata.create_all)  # Recreate table

    # Ensure the data file exists
    print(f"[INFO] Checking for the presence of CSV file at: {CSV_FILE_PATH}")
    if not os.path.exists(CSV_FILE_PATH):
        print(f"[ERROR] CSV file not found at {CSV_FILE_PATH}")
        return

    # Step 1: Load the CSV File
    print(f"[INFO] Reading data from {CSV_FILE_PATH}...")
    data = pd.read_csv(CSV_FILE_PATH)
    print("[DEBUG] Original CSV Columns:", list(data.columns))

    # Step 2: Clean Column Headers
    data.columns = [col.strip().lower().replace(" ", "_") for col in data.columns]
    print("[DEBUG] Normalized CSV Columns:", list(data.columns))

    # Step 3: Rename columns to match database schema
    COLUMN_MAP = {
        "service_date": "service_date",
        "submitted_procedure": "submitted_procedure",
        "plan/group_#": "plan_group",  # Key has been normalized
        "subscriber#": "subscriber_id",  # Key has been normalized
        "provider_npi": "provider_npi",
        "provider_fees": "provider_fees",
        "allowed_fees": "allowed_fees",
        "member_coinsurance": "member_coinsurance",
        "member_copay": "member_copay",
    }
    print("[DEBUG] Column Mapping:", COLUMN_MAP)

    print("[INFO] Renaming columns to match database schema...")
    data.rename(columns=COLUMN_MAP, inplace=True)
    print("[DEBUG] Columns after renaming:", list(data.columns))

    # Step 4: Ensure all required columns are present
    required_columns = [
        "service_date", "subscriber_id", "provider_npi", "submitted_procedure",
        "plan_group", "quadrant", "provider_fees", "allowed_fees",
        "member_coinsurance", "member_copay"
    ]
    print("[INFO] Validating that all required columns are present...")
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        print("[ERROR] Missing required columns in CSV:", missing_columns)
        raise KeyError(f"Required column(s) missing from the CSV file: {missing_columns}")
    print("[INFO] All required columns are present.")

    # Step 5: Transform Data
    print("[INFO] Transforming data for database insertion...")

    # Clean monetary values
    print("[DEBUG] Sample data before monetary value transformation:")
    print(data.head())

    monetary_columns = ["provider_fees", "allowed_fees", "member_coinsurance", "member_copay"]
    for col in monetary_columns:
        data[col] = data[col].replace({r"\$": "", ",": ""}, regex=True).astype(float)

    print("[DEBUG] Sample data after monetary value transformation:")
    print(data.head())

    # Calculate `net_fee`
    data["net_fee"] = data["provider_fees"] + data["member_coinsurance"] + data["member_copay"] - data["allowed_fees"]

    # Parse and normalize `service_date`
    data["service_date"] = pd.to_datetime(data["service_date"], format="%m/%d/%y %H:%M", errors="coerce")

    # Handle nullable fields
    data["quadrant"] = data["quadrant"].fillna("").astype(str)  # Use empty strings for quadrant
    data["plan_group"] = data["plan_group"].astype(str)

    # Convert IDs (e.g., `subscriber_id`, `provider_npi`) to integers
    data["subscriber_id"] = data["subscriber_id"].astype("int64")
    data["provider_npi"] = data["provider_npi"].astype("int64")

    print("[INFO] Data transformation complete.")

    # Step 6: Insert Data into Database
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
