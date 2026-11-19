"""Job sources. Each module has fetch() and normalize(); see base.py."""

from app.ingestion.sources import adzuna, greenhouse, lever

ADAPTERS = {"greenhouse": greenhouse, "lever": lever, "adzuna": adzuna}
