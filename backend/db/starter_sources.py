"""
Turn on a starter set of real job sources for Alberta, all checked against
the live services on 2026-11-19:

    python -m db.starter_sources

  Government of Alberta  RSS feeds for data, analyst and IT searches
  Ashby                  Jobber (Edmonton), Neo Financial and Benevity (Calgary),
                         and Canadian companies hiring remote in Canada
  Greenhouse             Robots and Pencils, Orennia (Calgary), Darkhorse (Edmonton),
                         plus large boards with remote-in-Canada roles

Only postings in your area are kept (your profile's cities and province, or
remote work open to Canada), so fill in your profile's locations first.
Existing identifiers are kept; these are added. Edit them any time in
Settings > Sources.
"""

import psycopg

from app.config import get_settings

GOA = "https://jobpostings.alberta.ca/feeds/{}/?locale=en_US"

STARTER = {
    "rss": [GOA.format(k) for k in ("data", "analyst", "information%20technology", "systems", "business", "technology")],
    "ashby": ["jobber", "neofinancial", "benevity", "koho", "wealthsimple", "1password", "cohere"],
    "greenhouse": ["robotsandpencils", "orennia", "darkhorseviz", "gitlab", "databricks", "samsara"],
}


def main() -> None:
    with psycopg.connect(get_settings().database_url) as db:
        for source, identifiers in STARTER.items():
            current = db.execute("SELECT identifiers FROM source_settings WHERE source = %s", (source,)).fetchone()
            if current is None:
                raise SystemExit("Run the migrations first: python -m db.migrate")
            merged = list(dict.fromkeys([*current[0], *identifiers]))
            db.execute(
                "UPDATE source_settings SET enabled = true, identifiers = %s WHERE source = %s", (merged, source)
            )
            print(f"{source}: on, {len(merged)} identifiers")
        locations = db.execute("SELECT locations FROM candidate_profile LIMIT 1").fetchone()[0]
    if not locations:
        print("\nYour profile has no locations yet, so every posting would be kept. Add them on the Profile page first.")
    print("\nNow collect:  python -m app.ingestion.run")


if __name__ == "__main__":
    main()
