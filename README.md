# CodeRound GTM Lead Finder

Ranks outbound leads by **verified hiring evidence** pulled live from companies'
own applicant tracking systems — then back-tests that ranking against
CodeRound's real customers to check whether it actually works.

Python 3 standard library only. No API keys, no accounts, no paid services.

## Setup & run

```bash
python3 fetch_roles.py     # pull live open-role counts from job-board APIs
python3 enrich.py          # score and rank
python3 backtest.py        # validate against CodeRound's known customers
python3 test_enrich.py     # 24 tests
python3 test_fetch_roles.py # 10 tests
```

**One-time macOS fix.** Python installed from python.org does not register root
certificates, so `urllib` fails with `CERTIFICATE_VERIFY_FAILED` while `curl`
works. Run once:

```bash
/Applications/Python\ 3.14/Install\ Certificates.command
```

`fetch_roles.py` names this exact fix in its error output if it hits the problem.

## Architecture

```text
   Greenhouse API     Lever API      Ashby API        (public, no auth)
          \               |               /
           \              |              /
            ------> fetch_roles.py <-----
                         │  counts engineering roles only
                         │  caches to roles_cache.json
                         ▼
                 seed_companies.csv          ← open_eng_roles + evidence_url
                         │
                         ▼
                    enrich.py
         CLEAN → SCORE (3 signals) → EXPLAIN → OUTREACH → RANK
                         │
                         ▼
                 enriched_leads.csv
                         │
                         ▼
                    backtest.py              ← do real customers rank high?
```

## The API integration

Three public job-board APIs, no authentication:

| Provider | Endpoint |
|---|---|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{slug}/jobs` |
| Lever | `api.lever.co/v0/postings/{slug}?mode=json` |
| Ashby | `api.ashbyhq.com/posting-api/job-board/{slug}` |

**Each company's provider and slug are stored in the CSV, resolved by hand once.**
That is deliberate. Guessing slugs at runtime returns the wrong company:
`greenhouse/slice` is a firm in North Macedonia, not India's Slice, and
`ashby/navi` is a San Francisco hardware startup, not Navi the Indian fintech.
Entity resolution is the hard part of this kind of enrichment, and the honest
fix is to resolve once and record the answer rather than guess every run.

**Only engineering roles are counted.** A "Sales Engineer" is a GTM hire, not an
engineering hire — counting it would inflate the strongest signal in the score.
Titles are matched against engineering terms, with GTM-flavoured titles excluded,
falling back to the posting's department when the title alone is ambiguous
(Ashby's "Member of Technical Staff").

**Failure handling.** Every call is wrapped: 404 → "board not found", timeout or
DNS → "network error", bad body → "response was not valid JSON". A failure sets
that lead to `unknown` and the run continues. Results are cached to
`roles_cache.json`, and `--offline` runs from cache alone, so a demo never
depends on the network.

## Scoring

| Signal | Max | Source |
|---|---|---|
| Verified open engineering roles | 6 | Live job-board API |
| Investor overlap with CodeRound's published VC list | 3 | Manual research |
| Funding stage | 2 | Manual research |

Role tiers: 50+ → 6, 30–49 → 5, 15–29 → 4, 7–14 → 3, 3–6 → 2, 1–2 → 1, 0 → 0.

**Thresholds: High ≥ 5, Medium ≥ 3** — recalibrated against the real
distribution once live data arrived. The first tiers were written before any
real counts existed and put 15 of 21 companies at maximum points, which is no
ranking at all.

**High additionally requires verified role data.** Investors plus stage max out
at 5, which clears the numeric threshold — the gate stops a lead reaching High
without the signal that actually means hiring. That is the stage-only failure
this scoring exists to prevent.

## Results

21 companies, all with live public job boards. **21/21 fetched successfully.**
Engineering role counts range 0 to 60.

```
Priority split: High 6/21, Medium 9/21, Low 6/21
Evidence coverage: investors 0/21, open roles 21/21
```

The stage-only baseline cannot score this list at all — no lead has a known
funding stage, so the original v1 scoring would return nothing. The job-board
data is doing all the work.

## Back-test — and it failed

Four companies in the list are published CodeRound customers (Sarvam AI,
CodeRabbit, Mem0, Pendo), so they act as known positives. If the scoring
captures "looks like a CodeRound customer", they should rank near the top.

```
Company       Rank    Score   Priority  Percentile
Sarvam AI     10/21   4       Medium    55.0
CodeRabbit    11/21   3       Medium    50.0
Pendo         15/21   3       Medium    30.0
Mem0          19/21   1       Low       10.0

Mean percentile   customers 36.2   others 53.2
VERDICT: FAIL - known customers rank clearly BELOW the rest.
```

**The scoring measures company size, not ICP fit.** Absolute role count rewards
the 40–60 role hyperscalers at the top of the list, while CodeRound's actual
customers are smaller startups hiring a handful of engineers — exactly the
profile the scorer pushes down.

This is the most useful result in the project. It is a real, measured
disconfirmation of my own hypothesis, and it points at a specific fix:
normalise role count by team size, or score role **velocity** (new postings in
the last 30 days) rather than absolute volume.

## Tests

**34 tests, standard library only, no network calls.**

- `test_enrich.py` (24) — scoring tiers and monotonicity, the High gate,
  verified-zero vs not-verified, sector normalisation (regression test for a
  real silent-fallback bug), row validation, de-duplication, outreach trust,
  and that a company is never its own social proof.
- `test_fetch_roles.py` (10) — each provider's JSON read into one shape,
  engineering-role classification, GTM titles excluded, department tie-breaks,
  unsupported providers rejected loudly, empty boards, and failure paths that
  make no network call.

## Limitations

1. **Role count is a volume measure, not an intent measure.** The back-test
   proves this. It is the main known defect.
2. **Investor and stage data are empty for this list.** The list was rebuilt
   around companies whose role data is retrievable; their funding data has not
   been re-researched, so two of three signals currently contribute nothing.
3. **Only three ATS providers.** Companies on Keka, Darwinbox, Zoho Recruit or
   a plain careers page cannot be read at all — which is why the original
   16-company Indian startup list had zero coverage and was replaced.
4. **Counts are a snapshot.** Cached at fetch time; no staleness expiry.
5. **Four known positives is too small** for the back-test to be statistically
   meaningful. It is directionally useful, not conclusive.

## What I'd build next

- **Role velocity instead of volume** — new postings in the last 30 days.
  Directly addresses the back-test failure.
- **Normalise by team size** so a 20-person startup hiring 5 engineers
  outranks a 2,000-person company hiring 40.
- **More ATS providers** (Workable, SmartRecruiters, Recruitee) to widen coverage.
- **Re-research investors and stage** for the rebuilt list, restoring the other
  two signals.
- **Store with `last_checked`** so stale evidence expires instead of being
  trusted forever.
- **Measure reply rate by priority bucket** — if High does not beat Low in
  practice, the scoring is wrong regardless of what the back-test says.

Deliberately not built: LinkedIn integration (no free API, against their terms,
and a worse signal than the company's own ATS), a database (21 rows), CRM sync,
a dashboard, and LLM-generated outreach.
