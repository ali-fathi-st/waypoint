"""
Try job-board identifiers without saving anything: shows whether each board
exists, how many postings it has, and which are in your area.

    python -m app.ingestion.check greenhouse gitlab stripe
    python -m app.ingestion.check lever plaid --near Edmonton Calgary Canada Remote

Use it to find board names before adding them in Settings > Sources.
"""

import argparse
import sys

from app.ingestion.sources import ADAPTERS
from app.ingestion.sources.base import Http, Invalid, SourceError


def check(source: str, identifiers: list[str], near: list[str], http: Http | None = None) -> list[dict]:
    adapter = ADAPTERS[source]
    http = http or Http()
    results = []
    for identifier in identifiers:
        context: dict = {"locations": []}
        try:
            raws = adapter.fetch(http, identifier, context)
        except (SourceError, Invalid) as error:
            results.append({"identifier": identifier, "ok": False, "error": str(error)})
            continue
        postings, bad = [], []
        for raw in raws:
            try:
                postings.append(adapter.normalize(raw, identifier, context))
            except (Invalid, KeyError, TypeError, ValueError) as error:
                bad.append(str(error))
        words = [w.lower() for w in near]
        local = [
            p for p in postings
            if not words or any(w in f"{p.location or ''} {p.work_arrangement}".lower() for w in words)
        ]  # fmt: skip
        results.append({
            "identifier": identifier, "ok": True, "company": postings[0].company_name if postings else None,
            "total": len(raws), "valid": len(postings), "invalid": bad, "local": local,
        })  # fmt: skip
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", choices=sorted(ADAPTERS))
    parser.add_argument("identifiers", nargs="+")
    parser.add_argument("--near", nargs="*", default=["Edmonton", "Calgary", "Alberta", "Canada", "Remote"],
                        help="words to look for in the location (default: Alberta, Canada, remote)")  # fmt: skip
    parser.add_argument("--show", type=int, default=5, help="how many nearby postings to list per board")
    args = parser.parse_args()
    for r in check(args.source, args.identifiers, args.near):
        if not r["ok"]:
            print(f"✗ {args.source}/{r['identifier']}: {r['error']}")
            continue
        print(
            f"✓ {args.source}/{r['identifier']} ({r['company']}): {r['total']} postings, {r['valid']} usable, "
            f"{len(r['local'])} near {', '.join(args.near) or 'anywhere'}"
        )
        for p in r["local"][: args.show]:
            salary = f", {p.salary_min:,}–{p.salary_max:,} {p.salary_currency}" if p.salary_min else ""
            print(f"    - {p.title} | {p.location or p.work_arrangement}{salary}")
        for reason in sorted(set(r["invalid"]))[:3]:
            print(f"    ! unusable: {reason}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
