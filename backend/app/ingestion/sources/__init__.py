"""Job sources. Each module has fetch() and normalize(); see base.py."""

from app.ingestion.sources import adzuna, ashby, greenhouse, lever, rss

ADAPTERS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby, "adzuna": adzuna, "rss": rss}
