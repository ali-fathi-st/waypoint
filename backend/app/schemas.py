"""
Response and request models: the shapes in docs/06-api-contract.md.

FastAPI uses these to validate what comes in and to shape what goes out.
Field names match the frontend's exactly (snake_case), so no renaming is
needed. If a field is missing here, the website reports it by name.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# ---- Allowed values (FastAPI rejects anything else with a 422) ----
JobSource = Literal["greenhouse", "lever", "adzuna", "manual"]
WorkArrangement = Literal["onsite", "hybrid", "remote", "unknown"]
EmploymentType = Literal["full_time", "part_time", "contract", "temporary", "internship", "unknown"]
ReviewStatus = Literal["new", "shortlisted", "dismissed"]
ReviewFilter = Literal["active", "new", "shortlisted", "dismissed", "all"]  # "active" = new + shortlisted
JobSort = Literal["match", "newest", "posted"]


class CompanyRef(BaseModel):
    id: str
    name: str
    website: str | None


class JobSkill(BaseModel):
    name: str
    required: bool
    evidence: str | None


class MatchFactor(BaseModel):
    key: str
    label: str
    weight: float = Field(ge=0, le=1)
    score: float = Field(ge=0, le=1)
    detail: str


class JobMatch(BaseModel):
    job_id: str
    score: int = Field(ge=0, le=100)
    summary: str
    factors: list[MatchFactor]
    matched_skills: list[str]
    missing_skills: list[str]
    method: Literal["rules", "rules+embeddings"]
    computed_at: datetime


class Job(BaseModel):
    id: str
    source: JobSource
    source_job_id: str
    title: str
    company: CompanyRef
    location: str | None
    work_arrangement: WorkArrangement
    employment_type: EmploymentType
    description: str
    url: str
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    posted_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime
    review_status: ReviewStatus
    skills: list[JobSkill]
    match: JobMatch | None
    # Filled in once applications exist (a later step). Always null for now.
    application_id: str | None = None


class JobPage(BaseModel):
    """One page of jobs. `total` counts every match, not just this page."""

    items: list[Job]
    total: int
    limit: int
    offset: int


class JobStatusUpdate(BaseModel):
    """Body of PATCH /api/v1/jobs/{id}."""

    review_status: ReviewStatus
