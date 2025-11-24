import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import admin, auth, curator, query
from .repository import lifespan

"""
app.py

FastAPI application entrypoint for PubMedFlo.
"""

def _allowed_origins() -> list[str]:
    """Read allowed CORS origins from env variable and return a cleaned list of origin strings. """
    # PUBMEDFLO_CORS_ORIGINS contains comma-separated allowed frontend domains.
    origins = os.getenv("PUBMEDFLO_CORS_ORIGINS")
    # If no env var is set, allow all origins ("*").
    if not origins:
        return ["*"]
    # Strips whitespace around each entry and split the string on commas.
    return [origin.strip() for origin in origins.split(",") if origin.strip()]

# lifespan tells FastAPI how to manage startup and shutdown for this app.
app = FastAPI(
    title="PubMedFlo Backend",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,           # Allows sending cookies/authorization headers from the browser.
    allow_methods=["*"],              # Allows all HTTP methods (GET, POST, PUT, DELETE, etc.).
    allow_headers=["*"],              # Allows all custom headers (like Authorization, X-Requested-With, etc.).
)

# Add routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(curator.router)
app.include_router(query.router)
