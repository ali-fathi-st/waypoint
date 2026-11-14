/**
 * The fields the frontend expects in each kind of record the backend sends.
 * The HTTP API checks every response against these lists, so if the backend
 * forgets a field (or misspells it), the page says exactly which one,
 * e.g. 'GET /jobs: item 0 is missing "first_seen_at"'.
 *
 * Full shapes, with types and examples: docs/06-api-contract.md
 */
export const REQUIRED_FIELDS = {
  job: [
    "id",
    "source",
    "source_job_id",
    "title",
    "company",
    "location",
    "work_arrangement",
    "employment_type",
    "description",
    "url",
    "salary_min",
    "salary_max",
    "salary_currency",
    "posted_at",
    "first_seen_at",
    "last_seen_at",
    "review_status",
    "skills",
    "match",
    "application_id",
  ],
  application: [
    "id",
    "job_id",
    "job",
    "status",
    "status_source",
    "applied_at",
    "follow_up_at",
    "resume_document_id",
    "cover_letter_document_id",
    "notes",
    "created_at",
    "updated_at",
    "events",
  ],
  document: [
    "id",
    "document_type",
    "title",
    "version",
    "status",
    "origin",
    "related_job_id",
    "related_job_title",
    "file_name",
    "size_bytes",
    "created_at",
    "updated_at",
  ],
  profile: [
    "id",
    "full_name",
    "email",
    "headline",
    "summary",
    "preferred_titles",
    "locations",
    "work_arrangements",
    "salary_min",
    "salary_max",
    "salary_currency",
    "exclusions",
    "skills",
    "experience",
    "education",
    "updated_at",
  ],
  settings: ["sources", "notifications", "account"],
  metrics: [
    "total_jobs",
    "new_jobs_7d",
    "shortlisted_jobs",
    "applications_submitted",
    "interviews",
    "responses",
    "response_rate",
    "follow_ups_due",
    "jobs_found_by_day",
    "recent_activity",
    "jobs_to_review",
    "generated_at",
  ],
  page: ["items", "total", "limit", "offset"],
};

/**
 * Returns the first missing field name, or null when everything is there.
 * Present-but-null is fine; absent is not.
 */
export function findMissingField(kind, record) {
  if (!record || typeof record !== "object") return "(the whole record)";
  return REQUIRED_FIELDS[kind].find((field) => !(field in record)) ?? null;
}
