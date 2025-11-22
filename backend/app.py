import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import admin, auth
from .repository import lifespan

"""
app.py

FastAPI application entrypoint for PubMedFlo.
"""

def _allowed_origins() -> list[str]:
    origins = os.getenv("PUBMEDFLO_CORS_ORIGINS")
    if not origins:
        return ["*"]
    return [origin.strip() for origin in origins.split(",") if origin.strip()]

# lifespan tells FastAPI how to manage startup and shutdown for this app.
app = FastAPI(
    title="PubMedFlo Backend",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
