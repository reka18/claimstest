from fastapi import FastAPI
from api import claims, health
from dependencies.limiter import init_limiter

app = FastAPI(on_startup=[init_limiter])

app.include_router(claims.router)
app.include_router(health.router)