"""
Response and request models: the shapes in docs/06-api-contract.md.

FastAPI uses these to validate what comes in and to shape what goes out.
Field names match the frontend's exactly (snake_case), so no renaming is
needed. If a field is missing here, the website reports it by name.
"""

from datetime import date, datetime
from typing import Annotated, Literal

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


# =============================================================== applications
ApplicationStatus = Literal[
    "saved", "preparing", "ready_for_review", "applied", "interview", "offer", "rejected", "withdrawn"
]  # fmt: skip
EventType = Literal[
    "created", "status_changed", "submission_confirmed", "note_updated",
    "follow_up_set", "document_linked", "interview_scheduled",
]  # fmt: skip
InterviewFormat = Literal["phone", "video", "onsite"]


class ApplicationJob(BaseModel):
    """The job's key details, copied into each application for display."""

    title: str
    company_name: str
    location: str | None
    url: str
    source: JobSource


class Interview(BaseModel):
    scheduled_for: datetime
    format: InterviewFormat
    with_whom: str | None = Field(default=None, max_length=200)


class ApplicationEvent(BaseModel):
    id: str
    application_id: str
    event_type: EventType
    occurred_at: datetime
    summary: str
    from_status: ApplicationStatus | None
    to_status: ApplicationStatus | None
    interview: Interview | None


class Application(BaseModel):
    id: str
    job_id: str
    job: ApplicationJob
    status: ApplicationStatus
    status_source: Literal["user", "integration"]
    applied_at: date | None
    follow_up_at: date | None
    resume_document_id: str | None
    cover_letter_document_id: str | None
    notes: str
    created_at: datetime
    updated_at: datetime
    events: list[ApplicationEvent]  # newest first


class ApplicationCreate(BaseModel):
    job_id: str
    notes: str = Field(default="", max_length=5000)


class ApplicationUpdate(BaseModel):
    """PATCH body: only the fields you send are changed."""

    status: ApplicationStatus | None = None
    notes: str | None = Field(default=None, max_length=5000)
    follow_up_at: date | None = None
    resume_document_id: str | None = None
    cover_letter_document_id: str | None = None


class SubmissionConfirm(BaseModel):
    applied_at: date
    follow_up_at: date | None = None
    resume_document_id: str | None = None
    cover_letter_document_id: str | None = None


# =============================================================== dashboard
class DayCount(BaseModel):
    date: date
    count: int


class ActivityItem(BaseModel):
    id: str
    occurred_at: datetime
    summary: str
    job_title: str
    company_name: str
    application_id: str
    job_id: str


class DashboardMetrics(BaseModel):
    total_jobs: int
    new_jobs_7d: int
    shortlisted_jobs: int
    applications_submitted: int
    interviews: int
    responses: int
    response_rate: float | None
    follow_ups_due: int
    jobs_found_by_day: list[DayCount]
    recent_activity: list[ActivityItem]
    jobs_to_review: list[Job]
    generated_at: datetime


# =============================================================== candidate
Month = Annotated[str, Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
Arrangement = Literal["onsite", "hybrid", "remote"]


class Skill(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    proficiency: Literal["familiar", "proficient", "expert"]
    years: float | None = Field(default=None, ge=0, le=80)


class Experience(BaseModel):
    id: str | None = None  # new rows have no id yet; the server assigns one
    title: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    start_month: Month
    end_month: Month | None = None  # null = current role
    description: str = Field(default="", max_length=5000)


class Education(BaseModel):
    id: str | None = None
    institution: str = Field(min_length=1, max_length=200)
    credential: str = Field(min_length=1, max_length=200)
    field: str | None = Field(default=None, max_length=200)
    end_month: Month | None = None
    in_progress: bool = False


class CandidateProfileInput(BaseModel):
    """PUT body: the whole profile (without id and updated_at)."""

    full_name: str = Field(default="", max_length=200)
    email: str = Field(default="", max_length=320)
    headline: str = Field(default="", max_length=300)
    summary: str = Field(default="", max_length=5000)
    preferred_titles: list[str] = Field(default_factory=list, max_length=50)
    locations: list[str] = Field(default_factory=list, max_length=50)
    work_arrangements: list[Arrangement] = Field(default_factory=list)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str = Field(default="CAD", pattern=r"^[A-Z]{3}$")
    exclusions: list[str] = Field(default_factory=list, max_length=50)
    skills: list[Skill] = Field(default_factory=list, max_length=200)
    experience: list[Experience] = Field(default_factory=list, max_length=50)
    education: list[Education] = Field(default_factory=list, max_length=20)


class CandidateProfile(CandidateProfileInput):
    id: str
    experience: list[Experience]
    education: list[Education]
    updated_at: datetime


# =============================================================== documents
DocumentType = Literal["resume", "cover_letter"]
DocumentStatus = Literal["draft", "ready", "archived"]


class Document(BaseModel):
    id: str
    document_type: DocumentType
    title: str
    version: int
    status: DocumentStatus
    origin: Literal["uploaded", "generated"]
    related_job_id: str | None
    related_job_title: str | None
    file_name: str | None
    size_bytes: int | None
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    status: DocumentStatus | None = None


# =============================================================== settings
CollectedSource = Literal["greenhouse", "lever", "adzuna"]


class RunSummary(BaseModel):
    fetched: int
    inserted: int
    updated: int
    skipped: int
    failed: int


class SourceSettings(BaseModel):
    source: CollectedSource
    enabled: bool
    identifiers: list[str]
    last_run_at: datetime | None
    last_run_status: Literal["never", "running", "succeeded", "partial", "failed"]
    last_run_summary: RunSummary | None
    credentials_configured: bool


class SourceChange(BaseModel):
    source: CollectedSource
    enabled: bool
    identifiers: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(max_length=50)


class Notifications(BaseModel):
    daily_digest: bool
    digest_hour: int = Field(ge=0, le=23)
    digest_min_score: int = Field(ge=0, le=100)
    follow_up_reminders: bool


class Account(BaseModel):
    display_name: str = Field(max_length=100)
    email: str = Field(max_length=320)
    timezone: str = Field(max_length=64)


class Settings(BaseModel):
    sources: list[SourceSettings]
    notifications: Notifications
    account: Account


class SettingsUpdate(BaseModel):
    sources: list[SourceChange] | None = None
    notifications: Notifications | None = None
    account: Account | None = None
