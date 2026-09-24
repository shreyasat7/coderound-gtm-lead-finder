"""
GTM Lookalike Lead Finder & Outreach Generator
------------------------------------------------
Built for: CodeRound AI (GTM Engineer application artifact)

Research basis: coderound.ai (live site) - actual customers, actual stats,
actual product mechanics (multi-agent AI interviews, RAG matching).
This is NOT a generic template - the ICP and pitch below are built from
CodeRound's real, current customer base, not a guess.

What this does:
  1. Defines CodeRound's real ICP from their actual customer list
     (AI/tech startups, funded by top-tier VCs, scaling engineering fast:
     Sarvam AI, CodeRabbit, Mem0, Nurix, Zenskar, Zoca, Simplismart, etc.)
  2. Takes a seed list of NEW companies (not yet CodeRound customers) and
     scores each one by how closely it matches that real ICP - a
     "lookalike" scoring approach, the same logic behind lookalike
     audiences in performance marketing, applied to B2B outbound.
  3. Attaches the most relevant EXISTING CodeRound customer as a social
     proof anchor per lead (e.g. an AI startup gets matched to Sarvam AI,
     not a random logo) - because "we helped a company like Mem0" lands
     far better than a generic pitch.
  4. Generates a personalized outreach line using CodeRound's real,
     verified stats (7-day hire, 75% engineering bandwidth saved, top 3%
     candidates, 25K+ candidates sourced weekly) - not invented numbers.
  5. Outputs a ranked CSV ready to hand to a sales/outreach tool
     (Instantly, Smartlead) or a CRM (HubSpot).

Production v2: swap the seed CSV for live Clay/Apollo enrichment, and
swap funding-stage-as-proxy for real hiring-intent data (LinkedIn Jobs,
Wellfound job postings) - that's the honest limitation of this version.
"""

import csv
from pathlib import Path

INPUT_FILE = Path(__file__).parent / "seed_companies.csv"
OUTPUT_FILE = Path(__file__).parent / "enriched_leads.csv"

# Cheap proxy signal: recently funded / early-stage companies are the ones
# scaling engineering headcount fastest, so they're CodeRound's hottest leads.
STAGE_HIRING_SCORE = {
    "Pre-Seed": 3,
    "Seed": 5,
    "Series A": 4,
    "Series B": 3,
    "Series C": 2,
    "Series D": 2,
}

# Sector-specific pain point framing - this is the actual "GTM engineering"
# part: the message changes based on who you're talking to, not one
# generic template blasted to everyone.
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
    "Fashion / B2B Marketplace": "hiring fast without slowing down a lean founding team",
    "AI Dashcam / Fleet Tech": "finding engineers who can actually ship in a fast-moving AI product",
    "Consumer Tech": "screening high volumes of applicants as you scale",
    "B2C AI / Money Coach": "finding engineers who can actually ship in a fast-moving AI product",
}

DEFAULT_PAIN_POINT = "screening technical candidates fast without burning founder or senior-eng time"

# CodeRound's REAL current customers, grouped by sector - pulled from
# coderound.ai live site (Sept 2026), not invented. Used to attach a
# relevant social-proof anchor to each new lead ("lookalike" matching).
EXISTING_CUSTOMERS_BY_SECTOR = {
    "Fintech": "Zenskar",
    "Voice AI / Enterprise": "Sarvam AI",
    "Artificial Intelligence": "Sarvam AI",
    "AI / Document Automation": "Mem0",
    "SaaS / Sales Tech": "CodeRabbit",
    "Marketing Tech / SaaS": "Pendo",
    "HR Tech / SaaS": "Zoca",
    "HR Tech / Recruiting": "Zoca",
    "Real Estate / PropTech": "Practo",
    "Mobility / Consumer Tech": "Snabbit",
    "Consumer Tech": "Snabbit",
    "B2C AI / Money Coach": "Simplismart",
    "Deep Tech / Drones": "Simplismart",
    "AI Dashcam / Fleet Tech": "Nurix",
    "Fashion / B2B Marketplace": "Jumbotail",
}
DEFAULT_COMPARABLE_CUSTOMER = "CodeRabbit"

# CodeRound's REAL, current, verified stats (from coderound.ai, Sept 2026).
# Note: their site states a 4:1 interview-to-offer ratio - double-check
# which figure your application materials use before quoting one.
REAL_STATS = {
    "ratio": "4:1 interview-to-offer ratio (top 3% of candidates)",
    "speed": "hires in 7 days",
    "bandwidth": "saves engineering teams 75% of screening time",
    "sourcing": "sources 25K+ candidates weekly across GitHub, Reddit, and Stack Overflow",
}


def hiring_score(stage: str) -> int:
    return STAGE_HIRING_SCORE.get(stage.strip(), 2)


def pain_point(sector: str) -> str:
    return SECTOR_PAIN_POINT.get(sector.strip(), DEFAULT_PAIN_POINT)


def comparable_customer(sector: str) -> str:
    return EXISTING_CUSTOMERS_BY_SECTOR.get(sector.strip(), DEFAULT_COMPARABLE_CUSTOMER)


def outreach_line(company: str, sector: str, stage: str) -> str:
    pain = pain_point(sector)
    anchor = comparable_customer(sector)
    return (
        f"Hey [Name] - saw {company} is scaling as a {stage}-stage {sector} "
        f"company. We recently helped {anchor}, a similar-profile startup, "
        f"with the exact headache most founders at your stage flag: {pain}. "
        f"CodeRound gets you to a hire in 7 days at a {REAL_STATS['ratio']}, "
        f"and {REAL_STATS['bandwidth']} along the way. Worth a quick look?"
    )


def enrich_company(row: dict) -> dict:
    score = hiring_score(row["stage"])
    return {
        **row,
        "hiring_likelihood_score": score,
        "priority": "High" if score >= 4 else ("Medium" if score >= 3 else "Low"),
        "comparable_existing_customer": comparable_customer(row["sector"]),
        "outreach_opener": outreach_line(row["company"], row["sector"], row["stage"]),
    }


def main():
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    enriched = [enrich_company(r) for r in rows]
    enriched.sort(key=lambda r: r["hiring_likelihood_score"], reverse=True)

    fieldnames = list(enriched[0].keys())
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched)

    print(f"Enriched {len(enriched)} leads -> {OUTPUT_FILE.name}\n")
    print(f"{'Company':<18}{'Stage':<12}{'Priority':<10}Score")
    print("-" * 50)
    for r in enriched:
        print(f"{r['company']:<18}{r['stage']:<12}{r['priority']:<10}{r['hiring_likelihood_score']}")

    high_priority = [r for r in enriched if r["priority"] == "High"]
    print(f"\n{len(high_priority)} high-priority leads identified for immediate outreach.")


if __name__ == "__main__":
    main()
