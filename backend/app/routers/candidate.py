"""
Your candidate profile. Saving it re-scores every job, because the score
compares each job against this profile.

The profile is one row in candidate_profile, plus its skills, experience and
education in their own tables. A PUT replaces the whole thing: delete the
child rows, insert the new ones, all in one transaction.
"""

import psycopg
from fastapi import APIRouter, Depends

from app.db import get_db
from app.schemas import CandidateProfile, CandidateProfileInput
from app.services.matching import rescore
from app.util import invalid, new_id, utc_now

router = APIRouter(prefix="/api/v1/candidate", tags=["candidate"])

PROFILE_ID = "me"  # single user for now


def read_profile(db: psycopg.Connection) -> CandidateProfile:
    row = db.execute("SELECT * FROM candidate_profile WHERE id = %s", (PROFILE_ID,)).fetchone()
    skills = db.execute(
        "SELECT name, proficiency, years FROM candidate_skills WHERE profile_id = %s ORDER BY position", (PROFILE_ID,)
    ).fetchall()
    experience = db.execute(
        "SELECT id, title, company, start_month, end_month, description FROM candidate_experience "
        "WHERE profile_id = %s ORDER BY position",
        (PROFILE_ID,),
    ).fetchall()
    education = db.execute(
        "SELECT id, institution, credential, field, end_month, in_progress FROM candidate_education "
        "WHERE profile_id = %s ORDER BY position",
        (PROFILE_ID,),
    ).fetchall()
    for skill in skills:  # numeric comes back as Decimal; whole years read better as 3 than 3.0
        if skill["years"] is not None:
            skill["years"] = int(skill["years"]) if skill["years"] == int(skill["years"]) else float(skill["years"])
    return CandidateProfile(**row, skills=skills, experience=experience, education=education)


def _clean_list(values: list[str]) -> list[str]:
    """Trim, drop blanks and case-insensitive duplicates, keep order."""
    seen, out = set(), []
    for value in values:
        text = value.strip()
        if text and text.lower() not in seen:
            seen.add(text.lower())
            out.append(text)
    return out


def write_profile(db: psycopg.Connection, body: CandidateProfileInput) -> None:
    if body.salary_min is not None and body.salary_max is not None and body.salary_max < body.salary_min:
        raise invalid("The maximum salary must be at least the minimum.", "salary_max")
    names = [s.name.strip().lower() for s in body.skills]
    if len(names) != len(set(names)):
        raise invalid("Each skill can only be listed once.", "skills")
    for i, e in enumerate(body.experience):
        if e.end_month and e.end_month < e.start_month:
            raise invalid("An end month can't be before the start month.", f"experience.{i}.end_month")

    db.execute(
        """
        UPDATE candidate_profile SET
            full_name = %s, email = %s, headline = %s, summary = %s,
            preferred_titles = %s, locations = %s, work_arrangements = %s,
            salary_min = %s, salary_max = %s, salary_currency = %s, exclusions = %s,
            updated_at = %s
        WHERE id = %s
        """,
        (
            body.full_name.strip(), body.email.strip(), body.headline.strip(), body.summary.strip(),
            _clean_list(body.preferred_titles), _clean_list(body.locations), list(dict.fromkeys(body.work_arrangements)),
            body.salary_min, body.salary_max, body.salary_currency, _clean_list(body.exclusions),
            utc_now(), PROFILE_ID,
        ),
    )  # fmt: skip
    for table in ("candidate_skills", "candidate_experience", "candidate_education"):
        db.execute(f"DELETE FROM {table} WHERE profile_id = %s", (PROFILE_ID,))  # table names are ours
    with db.cursor() as cur:
        cur.executemany(
            "INSERT INTO candidate_skills (profile_id, position, name, proficiency, years) VALUES (%s, %s, %s, %s, %s)",
            [(PROFILE_ID, i, s.name.strip(), s.proficiency, s.years) for i, s in enumerate(body.skills)],
        )
        cur.executemany(
            "INSERT INTO candidate_experience (id, profile_id, position, title, company, start_month, end_month, description) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            [(e.id or new_id("exp"), PROFILE_ID, i, e.title.strip(), e.company.strip(), e.start_month, e.end_month,
              e.description.strip()) for i, e in enumerate(body.experience)],
        )  # fmt: skip
        cur.executemany(
            "INSERT INTO candidate_education (id, profile_id, position, institution, credential, field, end_month, in_progress) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            [(e.id or new_id("edu"), PROFILE_ID, i, e.institution.strip(), e.credential.strip(), e.field,
              e.end_month, e.in_progress) for i, e in enumerate(body.education)],
        )  # fmt: skip


@router.get("", response_model=CandidateProfile)
def get_profile(db: psycopg.Connection = Depends(get_db)) -> CandidateProfile:
    return read_profile(db)


@router.put("", response_model=CandidateProfile)
def put_profile(body: CandidateProfileInput, db: psycopg.Connection = Depends(get_db)) -> CandidateProfile:
    """Replace the profile, then re-score every job against it."""
    write_profile(db, body)
    rescore(db)
    return read_profile(db)
