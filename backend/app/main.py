"""
The FastAPI application.

Run it (from the backend folder, with the virtual environment active):
    uvicorn app.main:app --reload
Then open http://localhost:8000/docs for the interactive API page.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import (
    applications,
    candidate,
    dashboard,
    documents,
    ingestion,
    jobs,
    settings,
)

app = FastAPI(
    title="Waypoint API",
    description=(
        "Backend for the Waypoint job search tracker. Shapes and rules: docs/06-api-contract.md. "
        "Waypoint never submits applications or contacts employers; it records what you did."
    ),
    version="1.0.0",
)

# CORS: lets the website (a different origin) call this API from the browser.
# The origins come from CORS_ORIGINS in .env. Credentials are allowed so a
# login cookie can work later; that's why origins must be listed, not "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)


# Waypoint has no sign-in yet and runs on your computer, so two more guards:
#  * Only answer to the host names in ALLOWED_HOSTS.
#  * Refuse changes (POST/PUT/PATCH/DELETE) sent by a browser from any other
#    website. CORS alone stops other sites READING responses, not SENDING
#    simple requests like a form upload. Scripts send no Origin header, so
#    they're unaffected.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=get_settings().allowed_host_list)

CHANGES = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def refuse_changes_from_other_sites(request: Request, call_next):
    origin = request.headers.get("origin")
    if request.method in CHANGES and origin and origin.rstrip("/") not in get_settings().cors_origin_list:
        return JSONResponse({"detail": "This website isn't allowed to make changes (see CORS_ORIGINS)."}, 403)
    return await call_next(request)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Quick check that the API is running."""
    return {"status": "ok"}


for module in (jobs, applications, dashboard, candidate, documents, settings, ingestion):
    app.include_router(module.router)
