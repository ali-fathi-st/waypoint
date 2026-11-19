"""
Find skills in a job description, and decide which are required.

Rules, no AI: each known skill is searched for as a whole word. A skill is
"nice to have" when it appears under a heading like "Nice to have" /
"Preferred" / "Bonus", or on a line that says so ("... is an asset");
otherwise it's required. The line it was found on is kept as evidence, so
the job page can show why.

The vocabulary is your profile's skills plus the common ones below, so the
skills you list always get looked for.
"""

import re

COMMON_SKILLS = [
    "Python", "SQL", "PostgreSQL", "MySQL", "SQL Server", "T-SQL", "Oracle", "Snowflake", "BigQuery",
    "Redshift", "Databricks", "Spark", "PySpark", "Kafka", "Airflow", "dbt", "Prefect", "Dagster",
    "Pandas", "NumPy", "scikit-learn", "TensorFlow", "PyTorch", "R", "Scala", "Java", "JavaScript",
    "TypeScript", "Go", "C#", ".NET", "C++", "Rust", "Bash", "PowerShell", "Linux", "Windows Server",
    "Git", "GitHub Actions", "CI/CD", "Docker", "Kubernetes", "Terraform", "AWS", "Azure", "GCP",
    "Azure Data Factory", "Synapse", "Microsoft Fabric", "Power BI", "Tableau", "Looker", "Excel",
    "Power Automate", "Power Apps", "SharePoint", "Dynamics 365", "Salesforce", "ServiceNow",
    "REST APIs", "GraphQL", "FastAPI", "Django", "Flask", "React", "Node.js", "HTML", "CSS",
    "ETL", "ELT", "Data Modeling", "Data Warehousing", "Machine Learning", "Statistics",
    "Active Directory", "Entra ID", "Intune", "Networking", "Agile", "Jira",
]  # fmt: skip

ALIASES = {
    "REST APIs": ["rest api", "rest apis", "restful"],
    "Power BI": ["power bi", "powerbi"],
    "Node.js": ["node.js", "nodejs"],
    "CI/CD": ["ci/cd", "ci / cd", "continuous integration"],
    "Data Modeling": ["data modeling", "data modelling", "dimensional model"],
    "Data Warehousing": ["data warehouse", "data warehousing"],
    "Machine Learning": ["machine learning"],
    "GCP": ["gcp", "google cloud"],
    "Entra ID": ["entra id", "azure ad", "azure active directory"],
    "PostgreSQL": ["postgresql", "postgres"],
}

PREFERRED_HEADING = re.compile(
    r"nice[- ]to[- ]have|preferred|bonus|desired|desirable|assets?\b|a plus|good to have|extra credit", re.I
)
REQUIRED_HEADING = re.compile(
    r"requirements|required|qualifications|what you bring|what you.ll need|must[- ]have|you have|"
    r"about you|who you are|skills|experience",
    re.I,
)
PREFERRED_LINE = re.compile(r"\b(is|are|would be|considered)( an?)? (asset|plus|bonus)\b|nice to have|preferred", re.I)


def _pattern(term: str) -> re.Pattern:
    # Whole word, but allow symbols in names like C#, C++, .NET, Node.js
    return re.compile(r"(?<![\w.#+])" + re.escape(term.lower()) + r"(?![\w#+]|\.\w)")


def _is_heading(line: str) -> bool:
    stripped = line.strip().rstrip(":")
    return bool(stripped) and not stripped.startswith("- ") and len(stripped) <= 60 and len(stripped.split()) <= 8


def extract_skills(description: str, extra_vocabulary: list[str] = ()) -> list[dict]:
    """[{'name': 'SQL', 'required': True, 'evidence': 'Strong SQL skills'}, ...] in order found."""
    vocabulary: dict[str, list[str]] = {}
    for name in [*extra_vocabulary, *COMMON_SKILLS]:
        key = name.strip().lower()
        if key and key not in {k.lower() for k in vocabulary}:
            vocabulary[name.strip()] = ALIASES.get(name.strip(), [name.strip()])
    patterns = {name: [_pattern(t) for t in terms] for name, terms in vocabulary.items()}

    found: dict[str, dict] = {}
    section_preferred = False
    for raw_line in description.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if _is_heading(line):
            if PREFERRED_HEADING.search(line):
                section_preferred = True
            elif REQUIRED_HEADING.search(line):
                section_preferred = False
        is_bullet = line.startswith("- ")
        if not is_bullet and not _is_heading(line) and len(line.split()) > 12:
            section_preferred = False  # a full paragraph ends the list above it
        # Paragraphs are checked sentence by sentence, so "X is an asset" only marks X.
        pieces = [line] if is_bullet else re.split(r"(?<=[.!?])\s+", line)
        for piece in pieces:
            lower = piece.lower()
            for name, pats in patterns.items():
                if name in found or not any(p.search(lower) for p in pats):
                    continue
                preferred = section_preferred or bool(PREFERRED_LINE.search(piece))
                found[name] = {"name": name, "required": not preferred, "evidence": piece.removeprefix("- ")[:200]}
    # A one-letter language like "R" or "Go" only counts when written in capitals.
    for name in ("R", "Go"):
        if name in found and not re.search(rf"(?<![\w]){name}(?![\w])", description):
            del found[name]
    return list(found.values())
