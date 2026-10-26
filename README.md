# CodeRound GTM Lead Finder

A rule-based GTM engineering prototype: it turns a seed list of companies into a
ranked outreach list where **every ranking is backed by evidence you can click
through to**.

Zero dependencies. Python 3 standard library only.

## Setup & run

```bash
python3 enrich.py        # run the pipeline
python3 test_enrich.py   # run the tests (no install needed)
pytest -q                # same tests, if you have pytest
```

## The workflow

```text
seed_companies.csv
        │
        ▼
  CLEAN    normalise sectors, drop incomplete rows, de-duplicate,
           log every fallback to stderr
        │
        ▼
  SCORE    three signals, weighted:
             open engineering roles   0-6 pts   (observed behaviour)
             investor ICP overlap     0-3 pts   (CodeRound's published qualifier)
             funding stage            0-2 pts   (proxy, tiebreaker only)
        │
        ▼
  EXPLAIN  score_reason in plain English + evidence_url per lead
        │
        ▼
  OUTREACH sector-aware opener, real published stats, real customer anchor
        │
        ▼
  EVALUATE compare against the stage-only baseline
        │
        ▼
enriched_leads.csv  (ranked, auditable)
```

## Scoring rationale

| Signal | Max | Why this weight |
|---|---|---|
| Verified open engineering roles | 6 | A posted job is **observed behaviour**, not an inference. It is the only signal here that directly means "this company is hiring engineers right now". |
| Investor overlap with CodeRound's ICP | 3 | coderound.ai carries a logo strip titled *"Trusted by startups funded by"* (YC, Peak XV, Accel, Lightspeed, Elevation, Nexus, Antler, Better Capital, Titan, Together Fund). That is CodeRound publicly stating its own ICP qualifier, so matching on it is defensible rather than invented. |
| Funding stage | 2 | Kept only as a tiebreaker. Being young correlates with hiring, but it does not *mean* hiring. v1 of this tool scored on stage alone and flagged 12 of 16 leads "High" — a prioritiser that prioritises three quarters of the list has not prioritised anything. |

**Thresholds:** High ≥ 7/11, Medium ≥ 4/11, else Low. Tuned so that "High"
requires real hiring evidence *plus* ICP fit — a company cannot reach High on
funding stage alone.

**Verified zero vs. not verified.** A blank evidence cell means "not researched",
which the tool reports separately from a confirmed `0`. Both score 0 points, but
only one is trustworthy. Conflating them is how bad GTM data quietly gets
believed.

## Data sources

| Field | Source | How it is obtained |
|---|---|---|
| company, sector, stage, location, founded_year | Public company information | Hand-compiled seed list of real Indian startups |
| investors | Public funding announcements (Entrackr, Inc42, DealStreetAsia, Venture Intelligence) | AI-assisted search, each result verified against a named article — **14 of 16 verified**, 2 marked `unknown` |
| open_eng_roles | Company careers pages | **0 of 16 verified** — see RESEARCH_NOTES.md §2 for why |
| evidence_url | The article the evidence was read from | Recorded per lead |
| CodeRound customers, stats | coderound.ai (live site) | Verbatim: 7-day hire, 4:1 interview-to-offer, top 3%, 75% bandwidth saved, 25K+ sourced weekly |

Nothing in this repository claims a CodeRound customer relationship, a hiring
intent, or a performance metric that is not published on coderound.ai or
recorded with a source URL.

### Evidence status

The seed list holds 16 companies. It started at 20 — four were removed because
no public source could confirm their investors, sector or current stage, and a
lead that cannot be sourced should not be ranked at all.

`investors` is researched and sourced for 14 of the remaining 16. `open_eng_roles`
is `unknown` for all 16 — careers pages 404, redirect to third-party ATS boards,
or render via JavaScript, and one apparent "zero jobs" result turned out to have
a filter applied. Rather than guess, the tool records `unknown` and **refuses to
rank any lead High without that signal**. See `RESEARCH_NOTES.md`.

That is the honest state of the data, and it is the gap a jobs API closes.

## Tests

19 tests, covering the failures that actually matter in GTM data work:

- scoring tiers for each signal
- blank evidence treated as unverified, not as a verified zero
- unreadable values (`"three"`) do not crash the run
- **regression:** `Fintech / SMB SaaS` resolves to Fintech instead of silently
  falling through to the wrong customer anchor (this was a real bug in v1,
  found in the tool's own output)
- unknown sectors warn instead of failing silently
- rows missing required columns are skipped with a line number
- duplicate companies are removed
- empty input does not crash
- outreach never claims an unverifiable relationship

## Limitations

1. **The evidence is gathered by hand.** 20 companies is tractable; 10,000 is
   not. The manual lookup is the bottleneck, not the scoring logic.
2. **Open-role counts are a point-in-time snapshot.** They go stale within
   weeks and there is no re-check.
3. **Sector → customer matching is approximate.** It is a hand-built map over
   CodeRound's public logo strip, matched on engineering-hiring profile rather
   than exact industry. It approximates "similar company"; it does not measure it.
4. **The weights are judgment calls.** 6/3/2 is reasoned, not fitted to
   outcome data. With reply-rate data I would tune them.
5. **No contact-level data.** The opener ships with a `[Name]` placeholder; a
   real send needs a contact source.
6. **The outreach is segment-level, not individual.** It varies by sector,
   stage and role count — not by person.

## What I would build next

- **Jobs API** (LinkedIn/Wellfound) instead of manual role lookup — this is the
  single highest-value change, and it is the only thing standing between this
  prototype and real scale.
- **De-duplicate by domain, not company name** — "Zolve" and "Zolve Inc" are the
  same lead; the current name-based dedupe misses that.
- **Store in a database** with a `last_checked` timestamp, so stale evidence
  expires instead of being trusted forever.
- **Measure what works:** reply rate and meetings booked per 100 leads,
  segmented by priority bucket. If High does not outperform Low, the scoring is
  wrong and should be retuned or thrown away.
- **CRM sync** (HubSpot) so the ranked list lands where the sales team works.

Deliberately not built: LLM-generated outreach, live job-board scraping, and a
dashboard. Each adds demo risk and dependency weight without making the core
qualification logic any more defensible.
