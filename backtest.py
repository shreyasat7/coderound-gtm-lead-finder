"""
Back-test: does the scoring actually rank CodeRound's real customers highly?

A lead scorer is a hypothesis. The only honest way to check it is to run it
over companies whose answer you already know. CodeRound publishes its customer
list on coderound.ai, and four of those companies are in the seed list with
live, public job boards - so they act as known positives.

If the scoring is capturing "looks like a CodeRound customer", those four
should land near the top. If they don't, the scoring is measuring something
else, and this script says so.

Usage:  python3 backtest.py        (run enrich.py first)
"""

import csv
import sys
from pathlib import Path

ENRICHED = Path(__file__).parent / "enriched_leads.csv"

# Published on coderound.ai's customer logo strip, and present in this seed
# list with a verifiable public job board.
KNOWN_CUSTOMERS = {"sarvam ai", "coderabbit", "mem0", "pendo"}


def percentile_rank(position: int, total: int) -> float:
    """100 = top of the list, 0 = bottom."""
    if total <= 1:
        return 100.0
    return round((total - position) / (total - 1) * 100, 1)


def main() -> int:
    if not ENRICHED.exists():
        print("ERROR: enriched_leads.csv not found - run python3 enrich.py first",
              file=sys.stderr)
        return 1

    rows = list(csv.DictReader(open(ENRICHED, newline="", encoding="utf-8")))
    if not rows:
        print("ERROR: enriched_leads.csv is empty", file=sys.stderr)
        return 1

    # enrich.py already wrote the file sorted best-first.
    total = len(rows)
    customers, others = [], []
    for i, row in enumerate(rows):
        entry = {
            "company": row["company"],
            "rank": i + 1,
            "score": int(row["hiring_likelihood_score"]),
            "priority": row["priority"],
            "pct": percentile_rank(i + 1, total),
        }
        (customers if row["company"].strip().lower() in KNOWN_CUSTOMERS else others).append(entry)

    if not customers:
        print("ERROR: no known customers found in the list - nothing to test against",
              file=sys.stderr)
        return 1

    print(f"BACK-TEST  -  {len(customers)} known CodeRound customers vs "
          f"{len(others)} other companies, {total} total\n")
    print(f"{'Company':<14}{'Rank':<8}{'Score':<8}{'Priority':<10}Percentile")
    print("-" * 54)
    for c in sorted(customers, key=lambda r: r["rank"]):
        print(f"{c['company']:<14}{str(c['rank']) + '/' + str(total):<8}"
              f"{c['score']:<8}{c['priority']:<10}{c['pct']}")

    cust_mean = sum(c["pct"] for c in customers) / len(customers)
    other_mean = sum(o["pct"] for o in others) / len(others)
    cust_score = sum(c["score"] for c in customers) / len(customers)
    other_score = sum(o["score"] for o in others) / len(others)

    print(f"\nMean percentile   customers {cust_mean:.1f}   others {other_mean:.1f}")
    print(f"Mean score        customers {cust_score:.2f}   others {other_score:.2f}")

    top_half = sum(1 for c in customers if c["pct"] >= 50)
    print(f"Customers in top half: {top_half}/{len(customers)}")

    print("\nVERDICT")
    if cust_mean > other_mean + 10:
        print("  PASS - known customers rank clearly above the rest.")
        print("  The scoring is picking up something real about CodeRound's ICP.")
    elif cust_mean < other_mean - 10:
        print("  FAIL - known customers rank clearly BELOW the rest.")
        print("  The scoring is measuring something other than ICP fit.")
        print("  Most likely cause: open-role count scales with company size, and")
        print("  CodeRound's customers are smaller startups hiring a handful of")
        print("  engineers - not the 40-60 role hyperscalers topping this list.")
        print("  Fix: normalise role count by team size, or score role VELOCITY")
        print("  (new postings in the last 30 days) instead of absolute volume.")
    else:
        print("  INCONCLUSIVE - no clear separation between the two groups.")
        print("  With only 4 known positives this test cannot say much either way;")
        print("  it needs the full customer list to be meaningful.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
