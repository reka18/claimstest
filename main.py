from fastapi import FastAPI
from api import claims, health
from dependencies.limiter import init_limiter

"""
Main application entrypoint for the FastAPI service.

This module initializes the FastAPI app, registers routers, and runs
startup tasks like rate limiter initialization.

Routes:
    - /claims: Endpoints for creating and querying claim records.
    - /health: Health check endpoint to verify service status.

Startup:
    - init_limiter: Initializes the Redis-based rate limiter (FastAPILimiter).
"""

# Create the FastAPI app and register the rate limiter as a startup task
app = FastAPI(on_startup=[init_limiter])

# Register route modules
app.include_router(claims.router)
app.include_router(health.router)