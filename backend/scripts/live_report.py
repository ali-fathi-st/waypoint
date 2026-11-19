"""Print what a live collection run stored: used by the live-check workflow."""

from app.db import connect

with connect() as db:
    for r in db.execute("SELECT * FROM ingestion_runs ORDER BY id").fetchall():
        print(f"\n== {r['source']}: {r['status']} | fetched {r['fetched']}, new {r['inserted']}, "
              f"updated {r['updated']}, skipped {r['skipped']}, quarantined {r['failed']}")  # fmt: skip
        for e in r["errors"]:
            print(f"   ✗ {e['identifier']}: {e['error']}")
    print("\n== boards that worked")
    for r in db.execute(
        "SELECT source, split_part(c.name, '|', 1) AS company, count(*) AS n, "
        "count(*) FILTER (WHERE location ~* 'edmonton|calgary|alberta|canada|toronto|vancouver' "
        "OR (work_arrangement = 'remote' AND coalesce(location,'') !~* 'us|united states|europe|uk|emea|apac')) AS canada "
        "FROM jobs j JOIN companies c ON c.id = j.company_id GROUP BY 1, 2 ORDER BY 4 DESC, 3 DESC"
    ).fetchall():
        print(f"   {r['source']:<10} {r['company']:<35} {r['n']:>4} postings, {r['canada']:>3} Canada/remote")
    print("\n== quarantine reasons")
    for r in db.execute("SELECT source, reason, count(*) AS n FROM quarantine GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 15"):
        print(f"   {r['n']:>4}  {r['source']}: {r['reason'][:150]}")
    print("\n== field coverage")
    print("  ", db.execute(
        "SELECT count(*) AS jobs, count(posted_at) AS posted_at, count(salary_min) AS salary, "
        "count(*) FILTER (WHERE work_arrangement <> 'unknown') AS arrangement, "
        "count(*) FILTER (WHERE employment_type <> 'unknown') AS employment, "
        "count(*) FILTER (WHERE jsonb_array_length(skills) > 0) AS with_skills, "
        "round(avg(length(description))) AS avg_desc_len FROM jobs"
    ).fetchone())
    print("\n== best matches in Alberta / Canada / remote")
    for r in db.execute(
        "SELECT j.title, c.name, j.location, j.work_arrangement, j.match_score, j.salary_min, j.salary_max, "
        "j.match->>'summary' AS summary FROM jobs j JOIN companies c ON c.id = j.company_id "
        "WHERE j.location ~* 'edmonton|calgary|alberta|canada' OR j.work_arrangement = 'remote' "
        "ORDER BY j.match_score DESC NULLS LAST LIMIT 25"
    ):
        print(f"   {r['match_score']:>3} {r['title'][:50]:<50} | {r['name'][:22]:<22} | {(r['location'] or r['work_arrangement'])[:30]}")
    print("\n== two sample descriptions")
    for r in db.execute("SELECT source, title, left(description, 600) AS d, skills FROM jobs ORDER BY random() LIMIT 2"):
        print(f"\n--- {r['source']} | {r['title']}\n{r['d']}\nSKILLS: {[(s['name'], s['required']) for s in r['skills']]}")
