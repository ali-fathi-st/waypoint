"""
The FastAPI application.

Run it (from the backend folder, with the virtual environment active):
    uvicorn app.main:app --reload
Then open http://localhost:8000/docs for the interactive API page.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import jobs

app = FastAPI(
    title="Waypoint API",
    description="Backend for the Waypoint job search tracker. See docs/06-api-contract.md.",
    version="0.1.0",
)

# CORS: lets the website (a different origin) call this API from the browser.
# The origins come from CORS_ORIGINS in .env. Credentials are allowed so the
# login cookie works later; that's why origins must be listed, not "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Quick check that the API is running."""
    return {"status": "ok"}


app.include_router(jobs.router)
