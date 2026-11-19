"""
Dashboard numbers, computed in SQL. Definitions (docs/06):

  applications_submitted  applied, interview, offer or rejected, plus withdrawn after applying
  interviews              reached the interview stage (interview/offer, or an interview event)
  responses               submitted applications that heard back (interview, offer, rejection)
  response_rate           responses / submitted, or null when nothing is submitted
  follow_ups_due          applied/interview with a follow-up date today or earlier
  jobs_found_by_day       the last 14 days, oldest first, zero days included

"Today" is in your time zone (Settings > Account), not UTC.
"""

import psycopg
from fastapi import APIRouter, Depends

from app.db import get_db
from app.rows import SELECT_JOB, row_to_job
from app.schemas import ActivityItem, DashboardMetrics, DayCount
from app.util import account_timezone, today_in, utc_now

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

APPLICATION_COUNTS = """
    WITH apps AS (
        SELECT a.*,
               (a.status IN ('applied', 'interview', 'offer', 'rejected')
                OR (a.status = 'withdrawn' AND a.applied_at IS NOT NULL)) AS submitted,
               (a.status IN ('interview', 'offer')
                OR EXISTS (SELECT 1 FROM application_events e
                           WHERE e.application_id = a.id
                             AND (e.to_status = 'interview' OR e.event_type = 'interview_scheduled'))) AS reached_interview
        FROM applications a
    )
    SELECT
        count(*) FILTER (WHERE submitted)                                            AS applications_submitted,
        count(*) FILTER (WHERE reached_interview)                                    AS interviews,
        count(*) FILTER (WHERE submitted AND (reached_interview OR status IN ('offer', 'rejected'))) AS responses,
        count(*) FILTER (WHERE status IN ('applied', 'interview') AND follow_up_at <= %(today)s)    AS follow_ups_due
    FROM apps
"""

JOB_COUNTS = """
    SELECT
        count(*)                                                     AS total_jobs,
        count(*) FILTER (WHERE first_seen_at >= now() - interval '7 days') AS new_jobs_7d,
        count(*) FILTER (WHERE review_status = 'shortlisted')        AS shortlisted_jobs
    FROM jobs
"""

# generate_series makes one row per day, so days with no jobs still appear (as 0).
JOBS_BY_DAY = """
    SELECT day::date AS date, count(j.id) AS count
    FROM generate_series(%(today)s::date - 13, %(today)s::date, interval '1 day') AS day
    LEFT JOIN jobs j ON (j.first_seen_at AT TIME ZONE %(tz)s)::date = day::date
    GROUP BY day
    ORDER BY day
"""

RECENT_ACTIVITY = """
    SELECT e.id, e.occurred_at, e.summary, j.title AS job_title, c.name AS company_name,
           a.id AS application_id, a.job_id
    FROM application_events e
    JOIN applications a ON a.id = e.application_id
    JOIN jobs j ON j.id = a.job_id
    JOIN companies c ON c.id = j.company_id
    ORDER BY e.occurred_at DESC, e.id DESC
    LIMIT 8
"""


@router.get("/metrics", response_model=DashboardMetrics)
def metrics(db: psycopg.Connection = Depends(get_db)) -> DashboardMetrics:
    tz = account_timezone(db)
    today = today_in(tz)
    params = {"today": today, "tz": tz}
    apps = db.execute(APPLICATION_COUNTS, params).fetchone()
    jobs = db.execute(JOB_COUNTS).fetchone()
    by_day = [DayCount(**r) for r in db.execute(JOBS_BY_DAY, params).fetchall()]
    activity = [ActivityItem(**r) for r in db.execute(RECENT_ACTIVITY).fetchall()]
    to_review = db.execute(
        SELECT_JOB + " WHERE j.review_status = 'new' ORDER BY j.match_score DESC NULLS LAST, j.first_seen_at DESC LIMIT 5"
    ).fetchall()
    submitted = apps["applications_submitted"]
    return DashboardMetrics(
        **jobs,
        **apps,
        response_rate=apps["responses"] / submitted if submitted else None,
        jobs_found_by_day=by_day,
        recent_activity=activity,
        jobs_to_review=[row_to_job(r) for r in to_review],
        generated_at=utc_now(),
    )
