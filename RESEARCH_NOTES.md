# Research Notes — the earlier, investor-researched lead list

> **This documents a previous version of the lead list and is kept for the
> record.** It covers 16 Indian startups scored on manually researched investor
> data. That list was replaced once the job-board API integration landed: none
> of those 16 companies has a public board on Greenhouse, Lever or Ashby — they
> use Keka, Darwinbox or a plain careers form — so the strongest signal in the
> score could never be filled for any of them.
>
> The current list is 21 companies with live, retrievable hiring data. See
> `README.md`. The investor-overlap signal described below still exists in
> `enrich.py` and is still tested; it simply has no data on the current list,
> and re-researching it is listed as future work.

**Method:** web search against startup-funding press (Entrackr, Inc42, Entrepreneur
India, DealStreetAsia, Outlook Business, Venture Intelligence, People Matters)
plus company profiles (CB Insights, PitchBook, Wikipedia). Research was gathered
with AI-assisted search and then checked against named press sources. Every
investor list below traces to a named article, recorded per lead in the CSV's
`evidence_url` column. Anything that could not be traced to a source is marked
`unknown` rather than estimated.

---

## 1. Investors — 14 of 16 verified

| Company | Investors found | ICP match? | Confidence |
|---|---|---|---|
| HouseEazy | Antler; Chiratae; Alteria | **Antler** | High — Antler led seed, joined $7M Series A (Aug 2024) |
| Navana AI | Antler; Ronnie Screwvala; Sandeep Singhal | **Antler** | High — Antler India led $800K pre-Series A (Jul 2025) |
| Cautio | Antler; 9Unicorns; Venture Catalysts; 8i | **Antler** | High — Antler in pre-seed and ₹11 Cr seed |
| Namma Yatri | Blume; Antler; Google | **Antler** | High — Blume + Antler co-led $11M (Jul 2024) |
| Inamo | Antler; Prime Venture Partners; Shastra VC; Gemba | **Antler** | High — Antler in seed and $8M Series A (Mar 2026) |
| HireBound | Antler; Kalaari; Infinyte; CareerNet | **Antler** | High — $2M seed led by Kalaari (Feb 2026) |
| Pascal AI Labs | Antler; Kalaari; Norwest; Info Edge | **Antler** | High — $3.1M seed (Sep 2025) |
| Green Aero | Antler; pi Ventures; Rebalance | **Antler** | High — $1.6M seed led by pi Ventures (Jul 2025) |
| Zolve | Accel; Lightspeed; Creaegis; HSBC | **Accel, Lightspeed** | High — both named as participating existing investors in the Mar 2025 Series B |
| Zomentum | Accel; Elevation; Greenoaks; Eight Roads | **Accel, Elevation** | High — Accel + SAIF (now Elevation) seed 2020, both in $13M Series A 2021 |
| Jupiter Money | Peak XV; Tiger Global; Mirae; BeeNext; 3one4 | **Peak XV** | High — Peak XV co-led the 2021 Series C |
| Khatabook | Y Combinator; Sequoia; GGV; Tencent; B Capital | **YC, Sequoia** | High — both in the 2019 $25M Series A; Sequoia Surge company |
| Rocketium | Blume; Emergent; 021 Capital; 1Crowd | none | Medium — totals vary by provider, investor names consistent |
| Wint Wealth | Eight Roads; Blume; 3one4 | none | High — $15M Series A led by Eight Roads (May 2022) |

Two leads — **Redacto** and **Springworks** — are retained with `unknown`
investors. Redacto's only coverage is an Inc42 profile that does not name its
backers; Springworks' sources conflict badly on both round sizes and investor
names, so none were recorded.

### The strongest signal in the data

**Antler appears in 8 of the 16 companies — half the list — and Antler is on
CodeRound's published "Trusted by startups funded by" logo strip.**

This was not engineered; it fell out of the research. Antler runs a large India
pre-seed programme, so its portfolio is densely packed with the profile
CodeRound sells to: very young companies about to make their first engineering
hires. If CodeRound already has traction with Antler-backed startups, the Antler
portfolio is a warm, named, finite prospecting surface — considerably more
targeted than "Indian startups, Seed stage".

**Rocketium and Wint Wealth are verified non-matches.** Both have real,
well-sourced investor lists (Blume, Emergent, Eight Roads, 3one4) with zero ICP
overlap. They demonstrate that the signal discriminates, rather than simply
rewarding the companies that were researched most thoroughly.

---

## 2. Open engineering roles — 0 of 16 verified

Trustworthy live role counts could not be obtained, and none were estimated.

Results from four representative attempts:

| Company | Result |
|---|---|
| Zolve | `/careers` returned HTTP 404 |
| Springworks | redirects twice, to an external `goodfit.so` board |
| Zomentum | careers page links out to a Freshteam board; that board returned "no jobs found" **with a Remote-Only filter applied**, so even the zero is ambiguous |
| Rocketium | JavaScript-rendered; a static fetch returns only the page title |

Careers pages 404, redirect to third-party ATS boards, or render client-side,
and an apparent "zero jobs" result proved to be a filtered view rather than a
real zero. Since this signal carries the most weight in the score, estimating it
would corrupt the entire ranking. It is recorded as `unknown`, and no lead can
reach High priority without it.

This is the specific gap a jobs API would close, and the main reason the
pipeline is not yet suitable for a list of thousands.

---

## 3. Data-quality problems found in the seed list

Researching the companies surfaced errors in the list itself.

### Corrected (each traced to a named source)

| Company | Was | Now | Source basis |
|---|---|---|---|
| **Inamo** | Fintech, founded 2026 | Quick Commerce / Retail Tech, 2024 | Quick-commerce enablement (dark stores, brand ops). Multiple outlets. |
| **Green Aero** | Deep Tech / Drones | Deep Tech / Aerospace | Hydrogen & defence **aero engines**, incubated at IIT Delhi. No source mentions drones. |
| **Redacto** | AI / Document Automation | AI / Data Privacy | Inc42 describes it as AI data privacy & governance. *Single source — lower confidence.* |
| **Navana AI** | Seed | Series A | Raised ~₹40 Cr Series A, Sept 2026. |
| **Cautio** | founded 2024 | 2023 | Founders Ankit Acharya & Pranjal Nadhani, 2023. |
| **HireBound** | founded 2026 | 2024 | Founded 2024 by Sharad Vij & Kumar Vikramaditya. |
| **Pascal AI Labs** | founded 2025 | 2024 | Founded 2024 by Vibhav Viswanathan & Mithun Madhusudan. |
| **Springworks** | founded 2015 | 2014 | Founded 2014 as SpringRole, later rebranded. |

Three new sector keys were added to `enrich.py` so the corrected values resolve
to a customer anchor instead of the generic default: Quick Commerce / Retail
Tech → Jumbotail, Deep Tech / Aerospace → Nurix, AI / Data Privacy → Zenskar.

### Error found, no verified replacement — left unchanged

| Company | Problem | Why it was left alone |
|---|---|---|
| **Green Aero** | `founded 2024` | Sources split between 2022 and 2023. Conflicting, so unchanged rather than guessed. |

Correcting what can be sourced while explicitly declining to correct what
cannot is the same discipline the scoring applies: a value that cannot be
verified should not be silently replaced with a plausible one.

---

## 4. Four leads removed

The seed list started at 20. Four were dropped because no public source could
confirm them:

| Company | Why removed |
|---|---|
| **Bizup** | No usable coverage. Searches surfaced Fashinza, a different Gurugram B2B fashion marketplace. |
| **Navo** | Only a single paywalled aggregator listing, which contradicted the stated sector (B2B fashion wholesale, not Consumer Tech). |
| **Nudge** | No Mumbai B2C money-coach app found. Searches returned Nudge Money (New York, B2B), an Australian student app, and The/Nudge (an Indian nonprofit). |
| **Slice** | Stage unverifiable. It converted to a small finance bank and took a ~60% valuation cut; the Accel/Elevation/Peak XV round was **in talks**, not closed. |

A lead that cannot be verified should not sit in a list a salesperson is going
to act on, so these were removed rather than carried with empty evidence.

---

## 5. Current output

- **Priority split:** 0 High, 10 Medium, 6 Low out of 16.
- **Baseline comparison:** the stage-only scoring this replaced flagged 12 of 16
  as High.
- **Evidence coverage:** investors 14/16, open roles 0/16.

Nothing reaches High because High requires 7 of 11 points and 6 of those come
from verified open roles. The scorer reports incomplete evidence rather than
compensating for it.

---

## 6. Sources

Zolve — https://www.fintechfutures.com/digital-banking/neobank-start-up-zolve-raises-251m-in-mix-of-debt-and-equity
Jupiter — https://entrackr.com/news/jupiter-money-raises-15-mn-from-mirae-asset-beenext-and-3one4-capital-10606028
Khatabook — https://www.gunder.com/en/news-insights/client-news/khatabook-raises-series-a-funding
HouseEazy — https://entrackr.com/2024/08/exclusive-proptech-startup-houseeazy-raises-4-mn-in-series-a
Rocketium — https://en.wikipedia.org/wiki/Rocketium
Zomentum — https://inc42.com/buzz/zomentum-raises-13-mn-series-a-accel-elevation
Wint Wealth — https://news.ventureintelligence.com/private-equity/b2c-debt-investment-marketplace-wint-wealth-raises-%2415-m-led-by-eight-roads-
Namma Yatri — https://www.outlookbusiness.com/corporate/namma-yatri-raises-11-million-in-pre-series-a-led-by-blume-ventures-antler-others
Navana AI — https://media.dealstreetasia.com/stories/antler-navana-ai-449331
Cautio — https://entrackr.com/snippets/dashcam-startup-cautio-raises-rs-11-cr-in-seed-round-8938078
Inamo — https://india.entrepreneur.com/news-and-trends/prime-venture-partners-leads-usd-8-mn-investment-in-inamo/503082
HireBound — https://www.peoplematters.in/news/funding-and-investment/hirebound-raises-dollar2-million-to-automate-hiring-with-ai-48548
Pascal AI Labs — https://news.ventureintelligence.com/private-equity/fintech-focused-ai-saas-startup-pascal-labs-raises-%243.1-m-from-kalaari%2C-info-edge-ventures
Green Aero — https://entrackr.com/snippets/green-aero-raises-16-mn-in-seed-round-led-by-pi-ventures-9477236
Redacto — https://inc42.com/company/redacto/
