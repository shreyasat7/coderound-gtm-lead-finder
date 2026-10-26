"""
CodeRound GTM Lead Finder - evidence-backed lead scoring & outreach
-------------------------------------------------------------------
Built for: CodeRound AI (GTM Engineer application artifact)

What this does
  Takes a seed list of companies and turns it into a ranked outreach list,
  where every ranking is backed by evidence you can click through to.

  1. CLEAN    - normalises messy sector strings, drops incomplete rows,
                removes duplicates, and logs every fallback instead of
                silently guessing.
  2. SCORE    - ranks each company on THREE signals, not one:
                  a) verified open engineering roles  (observed behaviour)
                  b) investor overlap with CodeRound's published ICP
                  c) funding stage                    (weakest, tiebreaker)
  3. EXPLAIN  - every lead carries a score_reason in plain English and an
                evidence_url, so an SDR can audit the ranking in one click.
  4. OUTREACH - writes a sector-aware opener using CodeRound's real,
                published stats and a real customer as social proof.
  5. EVALUATE - compares this scoring against the naive stage-only
                baseline, so the improvement is measurable, not asserted.

Honest limitations (see README for the full list)
  - open_eng_roles and investors are researched MANUALLY and recorded in
    the seed CSV. A production version reads them from a jobs API and a
    funding database. The manual step is the bottleneck, not the logic.
  - Sector -> customer matching is a hand-built map over CodeRound's
    public logo strip. It approximates "similar profile", it does not
    measure it.
  - Nothing here claims a CodeRound customer relationship that is not
    published on coderound.ai.
"""

import csv
import sys
from pathlib import Path

INPUT_FILE = Path(__file__).parent / "seed_companies.csv"
OUTPUT_FILE = Path(__file__).parent / "enriched_leads.csv"

REQUIRED_COLUMNS = ("company", "sector", "stage")


# ---------------------------------------------------------------------------
# Signal 1: verified open engineering roles (strongest - observed behaviour)
# ---------------------------------------------------------------------------
# A company that has posted engineering roles is hiring. That is a fact we
# looked up, not a guess. Blank means "not researched yet", which scores 0
# but is reported separately from a verified zero - those are different
# things, and conflating them is how bad GTM data gets trusted.

UNKNOWN_MARKERS = {"", "unknown", "n/a", "na", "-", "?"}


def open_roles_points(raw) -> tuple:
    """Return (points, reason, verified). Max 6 points."""
    text = str(raw if raw is not None else "").strip()
    if text.lower() in UNKNOWN_MARKERS:
        return 0, "open roles: NOT VERIFIED", False
    try:
        count = int(float(text))
    except ValueError:
        return 0, f"open roles: unreadable value {text!r}", False
    if count < 0:
        return 0, f"open roles: invalid negative value ({count})", False
    if count >= 5:
        return 6, f"{count} open eng roles (hiring hard)", True
    if count >= 3:
        return 5, f"{count} open eng roles", True
    if count >= 1:
        return 3, f"{count} open eng role(s)", True
    return 0, "0 open eng roles (verified not hiring)", True


# ---------------------------------------------------------------------------
# Signal 2: investor overlap with CodeRound's published ICP
# ---------------------------------------------------------------------------
# coderound.ai carries a logo strip titled "Trusted by startups funded by".
# That is CodeRound publicly stating its own ICP qualifier, so matching on
# it is defensible rather than invented.

CODEROUND_ICP_INVESTORS = {
    "y combinator": "Y Combinator",
    "yc": "Y Combinator",
    "peak xv": "Peak XV",
    "peak xv partners": "Peak XV",
    "sequoia": "Sequoia",
    "sequoia capital": "Sequoia",
    "accel": "Accel",
    "lightspeed": "Lightspeed",
    "lightspeed venture partners": "Lightspeed",
    "elevation": "Elevation Capital",
    "elevation capital": "Elevation Capital",
    "nexus": "Nexus Venture Partners",
    "nexus venture partners": "Nexus Venture Partners",
    "antler": "Antler",
    "better capital": "Better Capital",
    "titan": "Titan Capital",
    "titan capital": "Titan Capital",
    "together fund": "Together Fund",
}


def investor_points(raw) -> tuple:
    """Return (points, reason, verified). Max 3 points."""
    text = str(raw if raw is not None else "").strip()
    if text.lower() in UNKNOWN_MARKERS:
        return 0, "investors: NOT VERIFIED", False
    matches = []
    for part in text.split(";"):
        canonical = CODEROUND_ICP_INVESTORS.get(normalise(part))
        if canonical and canonical not in matches:
            matches.append(canonical)
    if matches:
        return 3, f"backed by {', '.join(matches)} (matches CodeRound ICP)", True
    return 0, "no investor overlap with CodeRound ICP", True


# ---------------------------------------------------------------------------
# Signal 3: funding stage (weakest - a proxy, kept only as a tiebreaker)
# ---------------------------------------------------------------------------

STAGE_POINTS = {
    "pre-seed": 1,
    "seed": 2,
    "series a": 2,
    "series b": 1,
    "series c": 0,
    "series d": 0,
}

# The old v1 scoring, kept so the evaluation below is reproducible rather
# than a claim. Do not use it for ranking.
LEGACY_STAGE_SCORE = {
    "pre-seed": 3, "seed": 5, "series a": 4,
    "series b": 3, "series c": 2, "series d": 2,
}


def stage_points(stage: str) -> tuple:
    """Return (points, reason). Max 2 points."""
    key = normalise(stage)
    if key not in STAGE_POINTS:
        return 0, f"unrecognised stage {stage.strip()!r}"
    return STAGE_POINTS[key], f"{stage.strip()} stage"


# ---------------------------------------------------------------------------
# Sector handling - normalised so messy free text still matches
# ---------------------------------------------------------------------------

def normalise(text: str) -> str:
    """Lowercase, trim, and collapse internal whitespace."""
    return " ".join(str(text or "").strip().lower().split())


# Free-text sector values that mean an existing canonical sector. This is
# what stops 'Fintech / SMB SaaS' silently falling through to the default.
SECTOR_ALIASES = {
    "fintech / smb saas": "Fintech",
    "fintech / sme saas": "Fintech",
    "financial services": "Fintech",
    "ai": "Artificial Intelligence",
    "artificial intelligence / ml": "Artificial Intelligence",
    "proptech": "Real Estate / PropTech",
    "hr tech": "HR Tech / SaaS",
    "saas": "SaaS / Sales Tech",
}

SECTOR_PAIN_POINT = {
    "Fintech": "hiring engineers fast without compromising on technical bar, especially under compliance pressure",
    "SaaS / Sales Tech": "scaling your eng team without your senior engineers losing a week every sprint to first-round interviews",
    "Marketing Tech / SaaS": "screening technical candidates fast enough to keep up with your growth stage",
    "HR Tech / SaaS": "practicing what you preach - fast, fair, high-signal technical screening",
    "HR Tech / Recruiting": "practicing what you preach - fast, fair, high-signal technical screening",
    "Artificial Intelligence": "filtering signal from noise in an AI hiring market flooded with inflated resumes",
    "Voice AI / Enterprise": "finding engineers who can actually ship in a fast-moving AI product",
    "AI / Document Automation": "finding engineers who can actually ship in a fast-moving AI product",
    "Real Estate / PropTech": "hiring product engineers without your ops team getting buried in resume screening",
    "Mobility / Consumer Tech": "screening high volumes of applicants as you scale across cities",
    "Deep Tech / Drones": "finding rare, highly technical talent fast in a niche field",
    "Deep Tech / Aerospace": "finding rare, highly technical talent fast in a niche field",
    "Quick Commerce / Retail Tech": "hiring engineers fast enough to keep up with an operations business scaling city by city",
    "AI / Data Privacy": "hiring engineers who can move fast on an enterprise product without dropping the compliance bar",
    "Fashion / B2B Marketplace": "hiring fast without slowing down a lean founding team",
    "AI Dashcam / Fleet Tech": "finding engineers who can actually ship in a fast-moving AI product",
    "Consumer Tech": "screening high volumes of applicants as you scale",
    "B2C AI / Money Coach": "finding engineers who can actually ship in a fast-moving AI product",
}
DEFAULT_PAIN_POINT = "screening technical candidates fast without burning founder or senior-eng time"

# CodeRound's REAL current customers (coderound.ai logo strip). Matched on
# closest *engineering-hiring profile*, not on exact industry - an early
# consumer marketplace hires like another early consumer marketplace.
EXISTING_CUSTOMERS_BY_SECTOR = {
    "Fintech": "Zenskar",
    "Voice AI / Enterprise": "Sarvam AI",
    "Artificial Intelligence": "Sarvam AI",
    "AI / Document Automation": "Mem0",
    "SaaS / Sales Tech": "CodeRabbit",
    "Marketing Tech / SaaS": "Pendo",
    "HR Tech / SaaS": "Zoca",
    "HR Tech / Recruiting": "Zoca",
    "Real Estate / PropTech": "Snabbit",
    "Mobility / Consumer Tech": "Snabbit",
    "Consumer Tech": "Snabbit",
    "B2C AI / Money Coach": "Zoca",
    "Deep Tech / Drones": "Nurix",
    "Deep Tech / Aerospace": "Nurix",
    "Quick Commerce / Retail Tech": "Jumbotail",
    "AI / Data Privacy": "Zenskar",
    "AI Dashcam / Fleet Tech": "Nurix",
    "Fashion / B2B Marketplace": "Jumbotail",
}
DEFAULT_COMPARABLE_CUSTOMER = "CodeRabbit"

_PAIN_BY_KEY = {normalise(k): v for k, v in SECTOR_PAIN_POINT.items()}
_CUSTOMER_BY_KEY = {normalise(k): v for k, v in EXISTING_CUSTOMERS_BY_SECTOR.items()}


def canonical_sector(sector: str, warnings: list = None) -> str:
    """Resolve a free-text sector to a known key, logging any fallback."""
    key = normalise(sector)
    if key in _PAIN_BY_KEY:
        return key
    alias = SECTOR_ALIASES.get(key)
    if alias:
        return normalise(alias)
    if warnings is not None:
        warnings.append(f"unmapped sector {sector.strip()!r} - used generic fallback")
    return ""


def pain_point(sector_key: str) -> str:
    return _PAIN_BY_KEY.get(sector_key, DEFAULT_PAIN_POINT)


def comparable_customer(sector_key: str) -> str:
    return _CUSTOMER_BY_KEY.get(sector_key, DEFAULT_COMPARABLE_CUSTOMER)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
# Max = 6 (roles) + 3 (investors) + 2 (stage) = 11.
# Thresholds are tuned so High means "has verified hiring evidence AND fits
# the ICP" - not merely "is young".
HIGH_THRESHOLD = 7
MEDIUM_THRESHOLD = 4
MAX_SCORE = 11


def priority_for(score: int) -> str:
    if score >= HIGH_THRESHOLD:
        return "High"
    if score >= MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"


def score_lead(row: dict) -> dict:
    """Score one lead on all three signals and explain the result."""
    roles_pts, roles_reason, roles_verified = open_roles_points(row.get("open_eng_roles"))
    inv_pts, inv_reason, inv_verified = investor_points(row.get("investors"))
    stage_pts, stage_reason = stage_points(row.get("stage", ""))

    total = roles_pts + inv_pts + stage_pts
    return {
        "score": total,
        "priority": priority_for(total),
        "reason": "; ".join([roles_reason, inv_reason, stage_reason]),
        "evidence_verified": roles_verified and inv_verified,
    }


# CodeRound's REAL, published stats (coderound.ai).
REAL_STATS = {
    "ratio": "4:1 interview-to-offer ratio (top 3% of candidates)",
    "bandwidth": "saves engineering teams 75% of screening time",
}


def outreach_line(company: str, sector_key: str, stage: str, roles_raw) -> str:
    """Build the opener. Leads with the evidence when we actually have it."""
    anchor = comparable_customer(sector_key)
    pain = pain_point(sector_key)

    roles_text = str(roles_raw or "").strip()
    hook = f"saw {company} is scaling as a {stage.strip()}-stage company"
    if roles_text.isdigit() and int(roles_text) > 0:
        hook = f"saw {company} has {roles_text} open engineering role(s) right now"

    return (
        f"Hey [Name] - {hook}. We work with {anchor}, a startup with a "
        f"similar engineering-hiring profile, on exactly the headache most "
        f"teams at your stage flag: {pain}. CodeRound gets you to a hire in "
        f"7 days at a {REAL_STATS['ratio']}, and {REAL_STATS['bandwidth']} "
        f"along the way. Worth a quick look?"
    )


def enrich_company(row: dict, warnings: list = None) -> dict:
    sector_key = canonical_sector(row.get("sector", ""), warnings)
    scored = score_lead(row)
    return {
        **row,
        "hiring_likelihood_score": scored["score"],
        "priority": scored["priority"],
        "score_reason": scored["reason"],
        "evidence_verified": "yes" if scored["evidence_verified"] else "no",
        "comparable_existing_customer": comparable_customer(sector_key),
        "outreach_opener": outreach_line(
            row.get("company", ""), sector_key, row.get("stage", ""),
            row.get("open_eng_roles"),
        ),
    }


# ---------------------------------------------------------------------------
# Cleaning - the part a messy real-world CSV actually needs
# ---------------------------------------------------------------------------

def clean_rows(rows: list, warnings: list = None) -> list:
    """Drop rows missing required fields, and de-duplicate by company name."""
    cleaned, seen = [], set()
    for i, row in enumerate(rows, start=2):  # start=2 -> CSV line number
        missing = [c for c in REQUIRED_COLUMNS if not str(row.get(c) or "").strip()]
        if missing:
            if warnings is not None:
                warnings.append(f"line {i}: skipped - missing {', '.join(missing)}")
            continue
        key = normalise(row["company"])
        if key in seen:
            if warnings is not None:
                warnings.append(f"line {i}: skipped duplicate {row['company'].strip()!r}")
            continue
        seen.add(key)
        cleaned.append(row)
    return cleaned


def legacy_stage_only_priority(row: dict) -> str:
    """The v1 scoring, for the before/after evaluation only."""
    score = LEGACY_STAGE_SCORE.get(normalise(row.get("stage", "")), 2)
    return "High" if score >= 4 else ("Medium" if score >= 3 else "Low")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def main() -> int:
    warnings = []

    if not INPUT_FILE.exists():
        print(f"ERROR: input file not found: {INPUT_FILE}", file=sys.stderr)
        return 1

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        missing = [c for c in REQUIRED_COLUMNS if c not in header]
        if missing:
            print(f"ERROR: input is missing required column(s): {', '.join(missing)}",
                  file=sys.stderr)
            return 1
        raw_rows = list(reader)

    rows = clean_rows(raw_rows, warnings)
    if not rows:
        print("ERROR: no usable rows in input - nothing to enrich.", file=sys.stderr)
        for w in warnings:
            print(f"  warning: {w}", file=sys.stderr)
        return 1

    enriched = [enrich_company(r, warnings) for r in rows]
    # Sort by score, then company name so equal scores are stable/readable.
    enriched.sort(key=lambda r: (-r["hiring_likelihood_score"], r["company"].lower()))

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(enriched[0].keys()))
        writer.writeheader()
        writer.writerows(enriched)

    _report(enriched, rows, raw_rows, warnings)
    return 0


def _report(enriched, rows, raw_rows, warnings) -> None:
    print(f"Read {len(raw_rows)} rows -> {len(rows)} usable -> {OUTPUT_FILE.name}\n")

    print(f"{'Company':<18}{'Score':<8}{'Priority':<10}Why")
    print("-" * 100)
    for r in enriched:
        print(f"{r['company']:<18}{str(r['hiring_likelihood_score']) + '/' + str(MAX_SCORE):<8}"
              f"{r['priority']:<10}{r['score_reason'][:60]}")

    counts = {p: sum(1 for r in enriched if r["priority"] == p)
              for p in ("High", "Medium", "Low")}
    total = len(enriched)
    print(f"\nPriority split: High {counts['High']}/{total}, "
          f"Medium {counts['Medium']}/{total}, Low {counts['Low']}/{total}")

    # Honest evaluation against the naive baseline.
    legacy_high = sum(1 for r in rows if legacy_stage_only_priority(r) == "High")
    print(f"Evaluation: stage-only baseline flagged {legacy_high}/{total} as High; "
          f"evidence-backed scoring flags {counts['High']}/{total}.")

    roles_ok = sum(1 for r in rows if open_roles_points(r.get("open_eng_roles"))[2])
    inv_ok = sum(1 for r in rows if investor_points(r.get("investors"))[2])
    print(f"Evidence coverage: investors {inv_ok}/{total}, "
          f"open roles {roles_ok}/{total}.")
    if roles_ok < total:
        print(f"  -> {total - roles_ok} lead(s) have no verified open-role data, so "
              f"they cannot reach High ({HIGH_THRESHOLD}/{MAX_SCORE}) by design.")

    if warnings:
        print(f"\n{len(warnings)} data-quality warning(s):", file=sys.stderr)
        for w in warnings:
            print(f"  warning: {w}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
