"""
Application status rules: the Python copy of frontend/js/lib/status.js.
The website only uses its copy to decide which buttons to show; these are
the ones that are enforced.
"""

STATUS_LABEL = {
    "saved": "Saved",
    "preparing": "Preparing",
    "ready_for_review": "Ready for review",
    "applied": "Applied",
    "interview": "Interview",
    "offer": "Offer",
    "rejected": "Rejected",
    "withdrawn": "Withdrawn",
}

# Allowed moves by PATCH. "applied" is missing on purpose: the only way in is
# confirm-submission, which records that YOU submitted it on the employer's site.
STATUS_TRANSITIONS = {
    "saved": ["preparing", "withdrawn"],
    "preparing": ["saved", "ready_for_review", "withdrawn"],
    "ready_for_review": ["preparing", "withdrawn"],
    "applied": ["interview", "offer", "rejected", "withdrawn"],
    "interview": ["offer", "rejected", "withdrawn"],
    "offer": ["rejected", "withdrawn"],
    "rejected": [],
    "withdrawn": [],
}

CONFIRMABLE_STATUSES = ["saved", "preparing", "ready_for_review"]
SUBMITTED_STATUSES = ["applied", "interview", "offer", "rejected"]
FOLLOW_UP_STATUSES = ["applied", "interview"]
DEFAULT_FOLLOW_UP_DAYS = 14


def can_transition(current: str, to: str) -> bool:
    return to != "applied" and to in STATUS_TRANSITIONS[current]


def can_confirm_submission(status: str) -> bool:
    return status in CONFIRMABLE_STATUSES
