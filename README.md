# CodeRound GTM Lead Finder

A lightweight, rule-based GTM engineering prototype built for the CodeRound AI application.

The tool takes a seed list of companies and enriches each lead by:

- Prioritizing companies based on funding stage
- Matching companies to relevant CodeRound customer lookalikes
- Generating personalized outreach openers
- Assigning High / Medium / Low lead priority
- Sorting leads by priority
- Exporting the enriched results to a CSV file

## Why I Built This

For a GTM engineering workflow, the goal is not just to collect leads, but to identify which companies are worth contacting first and give the GTM team useful context for outreach.

I used CodeRound's publicly visible customer base to create a simple rule-based lookalike approach.

For example, a new company in a particular sector can be matched with a relevant existing CodeRound customer to provide contextual social proof in the outreach message.

## How It Works

```text
Seed Companies CSV
        ↓
Read company data
        ↓
Funding-stage scoring
        ↓
Sector → customer lookalike matching
        ↓
Generate personalized outreach
        ↓
Assign lead priority
        ↓
Sort leads
        ↓
Enriched Leads CSV