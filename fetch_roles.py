"""
Fetch REAL open engineering-role counts from public ATS job boards.

Why this exists
---------------
Funding stage is a proxy for hiring. An open job posting is the thing itself.
This script fills the `open_eng_roles` column in seed_companies.csv with a
number that came from the company's own applicant tracking system, plus the
URL it came from, so every count is auditable.

Three providers, all free and public - no API key, no account, no scraping:
  Greenhouse  https://boards-api.greenhouse.io/v1/boards/<slug>/jobs
  Lever       https://api.lever.co/v0/postings/<slug>?mode=json
  Ashby       https://api.ashbyhq.com/posting-api/job-board/<slug>

Each company's provider and slug are stored in the CSV, resolved once by hand.
That is deliberate: guessing slugs at runtime returns the WRONG company
(greenhouse/slice is a North Macedonian firm, not India's Slice).

Usage
-----
  python3 fetch_roles.py              # use cache if present, else call the API
  python3 fetch_roles.py --refresh    # ignore cache, re-fetch everything
  python3 fetch_roles.py --offline    # cache only, never touch the network
"""

import csv
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SEED_FILE = Path(__file__).parent / "seed_companies.csv"
CACHE_FILE = Path(__file__).parent / "roles_cache.json"

TIMEOUT = 10          # seconds per request
PAUSE = 0.3           # polite gap between requests
USER_AGENT = "coderound-gtm-lead-finder/1.0 (job-board research)"

BOARD_URL = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}

# Public, human-readable page for the same board - this is what goes in the
# CSV as evidence_url, because an interviewer can actually open it.
PUBLIC_URL = {
    "greenhouse": "https://boards.greenhouse.io/{slug}",
    "lever": "https://jobs.lever.co/{slug}",
    "ashby": "https://jobs.ashbyhq.com/{slug}",
}


# ---------------------------------------------------------------------------
# Deciding what counts as an engineering role
# ---------------------------------------------------------------------------
# CodeRound screens software engineers. A "Sales Engineer" is a GTM hire, not
# an engineering hire, so titles that merely contain "engineer" are not enough.

ENG_TERMS = (
    "engineer", "developer", "software", "programmer", "architect",
    "data scientist", "machine learning", "backend", "back-end", "frontend",
    "front-end", "fullstack", "full stack", "devops", "sre", "infrastructure",
    "platform", "android", "ios", "mobile",
)

NOT_ENG_TERMS = (
    "sales engineer", "solutions engineer", "solution engineer",
    "customer engineer", "support engineer", "field engineer",
    "engineering manager, people", "recruiter", "sourcer",
)


def is_engineering_role(title: str, department: str = "") -> bool:
    """True if this posting looks like a software-engineering hire."""
    t = (title or "").lower()
    if any(bad in t for bad in NOT_ENG_TERMS):
        return False
    if any(term in t for term in ENG_TERMS):
        return True
    # Fall back to the department when the title alone is ambiguous
    # (e.g. Ashby's "Member of Technical Staff").
    d = (department or "").lower()
    return d in ("engineering", "research", "r&d", "technology")


# ---------------------------------------------------------------------------
# Reading each provider's JSON into one common shape
# ---------------------------------------------------------------------------

def extract_postings(provider: str, payload) -> list:
    """Return [(title, department), ...] from a provider's raw JSON."""
    if provider == "greenhouse":
        return [(j.get("title", ""), "") for j in payload.get("jobs", [])]
    if provider == "ashby":
        return [(j.get("title", ""), j.get("department", "") or "")
                for j in payload.get("jobs", [])]
    if provider == "lever":
        return [(j.get("text", ""), (j.get("categories") or {}).get("team", "") or "")
                for j in payload]
    raise ValueError(f"unknown provider {provider!r}")


# ---------------------------------------------------------------------------
# The network call - every failure is caught and named
# ---------------------------------------------------------------------------

def fetch_board(provider: str, slug: str) -> dict:
    """
    Call one job board. Never raises - returns a dict describing what happened.
    {"ok": True, "total": int, "eng": int, "titles": [...]}  or
    {"ok": False, "error": "why it failed"}
    """
    if provider not in BOARD_URL:
        return {"ok": False, "error": f"unsupported provider {provider!r}"}

    url = BOARD_URL[provider].format(slug=slug)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            if response.status != 200:
                return {"ok": False, "error": f"HTTP {response.status}"}
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        reason = "board not found" if exc.code == 404 else f"HTTP {exc.code}"
        return {"ok": False, "error": reason}
    except urllib.error.URLError as exc:
        # Covers no network, DNS failure, timeout, and the macOS missing-certificate
        # problem. If you see CERTIFICATE_VERIFY_FAILED, run:
        #   /Applications/Python\ 3.x/Install\ Certificates.command
        return {"ok": False, "error": f"network error: {exc.reason}"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "response was not valid JSON"}
    except Exception as exc:                      # never let one board kill the run
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    try:
        postings = extract_postings(provider, payload)
    except (ValueError, AttributeError, TypeError) as exc:
        return {"ok": False, "error": f"unexpected payload shape: {exc}"}

    eng = [t for t, d in postings if is_engineering_role(t, d)]
    return {"ok": True, "total": len(postings), "eng": len(eng), "titles": eng[:5]}


# ---------------------------------------------------------------------------
# Cache - so the demo does not depend on the network
# ---------------------------------------------------------------------------

def load_cache() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text())
    except json.JSONDecodeError:
        print("warning: cache file unreadable, ignoring it", file=sys.stderr)
        return {}


def save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------

def main(argv) -> int:
    refresh = "--refresh" in argv
    offline = "--offline" in argv

    rows = list(csv.DictReader(open(SEED_FILE, newline="", encoding="utf-8")))
    cache = load_cache()
    fetched = cached = failed = skipped = 0

    for row in rows:
        provider = (row.get("ats_provider") or "").strip()
        slug = (row.get("ats_slug") or "").strip()
        if not provider or not slug:
            row["open_eng_roles"] = "unknown"
            skipped += 1
            continue

        key = f"{provider}/{slug}"
        if key in cache and not refresh:
            result = cache[key]
            cached += 1
        elif offline:
            result = {"ok": False, "error": "not in cache and --offline given"}
            failed += 1
        else:
            result = fetch_board(provider, slug)
            result["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            cache[key] = result
            time.sleep(PAUSE)
            fetched += 1
            if not result["ok"]:
                failed += 1

        if result.get("ok"):
            row["open_eng_roles"] = str(result["eng"])
            row["evidence_url"] = PUBLIC_URL[provider].format(slug=slug)
            print(f"  {row['company']:<14} {result['eng']:>3} eng / {result['total']:>3} total  ({key})")
        else:
            row["open_eng_roles"] = "unknown"
            print(f"  {row['company']:<14} FAILED: {result['error']}  ({key})", file=sys.stderr)

    if not offline:
        save_cache(cache)

    with open(SEED_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{len(rows)} companies: {fetched} fetched, {cached} from cache, "
          f"{failed} failed, {skipped} had no board configured")
    print(f"Wrote open_eng_roles + evidence_url -> {SEED_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
