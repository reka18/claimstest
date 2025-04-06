import os

"""
Configuration module for environment-based service URLs.

This module reads required configuration values from environment variables
and exposes them for use throughout the application. These include:
- DATABASE_URL: Used by SQLAlchemy to connect to the database.
- REDIS_URL: Used by FastAPI Limiter for rate limiting via Redis backend.

Make sure to define these variables in your environment or `.env` file.
"""

# SQLAlchemy-compatible database URL (e.g., for Postgres or SQLite async)
DATABASE_URL = os.getenv("DATABASE_URL")

# Redis connection string used for FastAPI rate limiting
REDIS_URL = os.getenv("REDIS_URL")