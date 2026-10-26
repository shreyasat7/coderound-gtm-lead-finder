"""
Tests for the CodeRound GTM lead finder.

Runs two ways:
    python3 test_enrich.py      (no install needed - stdlib only)
    pytest -q                   (if you have pytest)

Each test covers a failure that actually matters in GTM data work:
messy sector strings, missing columns, duplicates, and unverified evidence
being mistaken for a verified zero.
"""

import enrich


# --- Signal 1: open engineering roles --------------------------------------

def test_open_roles_scores_by_volume():
    assert enrich.open_roles_points("6")[0] == 6
    assert enrich.open_roles_points("3")[0] == 5
    assert enrich.open_roles_points("1")[0] == 3
    assert enrich.open_roles_points("0")[0] == 0


def test_blank_roles_is_unverified_not_a_verified_zero():
    """A blank cell means 'not researched', which is NOT the same as
    'confirmed not hiring'. Conflating them is how bad data gets trusted."""
    pts, reason, verified = enrich.open_roles_points("")
    assert (pts, verified) == (0, False)
    assert "NOT VERIFIED" in reason

    pts, reason, verified = enrich.open_roles_points("0")
    assert (pts, verified) == (0, True)
    assert "verified not hiring" in reason


def test_explicit_unknown_marker_is_treated_as_unverified():
    """'unknown' is how the seed CSV records research that could not be
    verified. It must read as unverified, not as garbage input."""
    for marker in ("unknown", "UNKNOWN", "n/a", "-"):
        assert enrich.open_roles_points(marker) == (0, "open roles: NOT VERIFIED", False)
        assert enrich.investor_points(marker) == (0, "investors: NOT VERIFIED", False)


def test_garbage_roles_value_does_not_crash():
    pts, reason, verified = enrich.open_roles_points("three")
    assert (pts, verified) == (0, False)
    assert "unreadable" in reason


# --- Signal 2: investor overlap --------------------------------------------

def test_investor_overlap_matches_coderound_icp():
    pts, reason, verified = enrich.investor_points("Accel; Some Angel")
    assert (pts, verified) == (3, True)
    assert "Accel" in reason


def test_investor_no_overlap_is_verified_zero():
    pts, _, verified = enrich.investor_points("Unknown Micro VC")
    assert (pts, verified) == (0, True)


def test_investor_blank_is_unverified():
    pts, reason, verified = enrich.investor_points("")
    assert (pts, verified) == (0, False)
    assert "NOT VERIFIED" in reason


# --- Sector normalisation (regression test for the v1 silent-fallback bug) --

def test_messy_sector_string_still_resolves():
    """'Fintech / SMB SaaS' silently fell through to the wrong customer in
    v1. It must now resolve to Fintech -> Zenskar."""
    warnings = []
    key = enrich.canonical_sector("Fintech / SMB SaaS", warnings)
    assert enrich.comparable_customer(key) == "Zenskar"
    assert warnings == []


def test_case_and_whitespace_are_ignored():
    assert enrich.canonical_sector("  FINTECH  ") == enrich.canonical_sector("Fintech")


def test_unknown_sector_warns_instead_of_failing_silently():
    warnings = []
    key = enrich.canonical_sector("Underwater Basket Weaving", warnings)
    assert enrich.comparable_customer(key) == enrich.DEFAULT_COMPARABLE_CUSTOMER
    assert len(warnings) == 1 and "unmapped sector" in warnings[0]


# --- Cleaning ---------------------------------------------------------------

def test_rows_missing_required_fields_are_skipped():
    warnings = []
    rows = [
        {"company": "Good Co", "sector": "Fintech", "stage": "Seed"},
        {"company": "", "sector": "Fintech", "stage": "Seed"},
        {"company": "No Stage Co", "sector": "Fintech", "stage": ""},
    ]
    kept = enrich.clean_rows(rows, warnings)
    assert [r["company"] for r in kept] == ["Good Co"]
    assert len(warnings) == 2


def test_duplicate_companies_are_removed():
    warnings = []
    rows = [
        {"company": "Zolve", "sector": "Fintech", "stage": "Seed"},
        {"company": " zolve ", "sector": "Fintech", "stage": "Seed"},
    ]
    assert len(enrich.clean_rows(rows, warnings)) == 1
    assert "duplicate" in warnings[0]


def test_empty_input_returns_empty_not_crash():
    assert enrich.clean_rows([], []) == []


# --- Scoring & priority -----------------------------------------------------

def test_full_evidence_lead_ranks_high():
    row = {"company": "X", "sector": "Fintech", "stage": "Seed",
           "investors": "Accel", "open_eng_roles": "4"}
    result = enrich.score_lead(row)
    assert result["score"] == 5 + 3 + 2  # roles + investors + stage
    assert result["priority"] == "High"
    assert result["evidence_verified"] is True


def test_young_company_without_evidence_cannot_rank_high():
    """The core fix: being Seed-stage is no longer enough to be High."""
    row = {"company": "Y", "sector": "Fintech", "stage": "Seed",
           "investors": "", "open_eng_roles": ""}
    result = enrich.score_lead(row)
    assert result["score"] == 2
    assert result["priority"] == "Low"
    assert result["evidence_verified"] is False


def test_priority_thresholds():
    assert enrich.priority_for(enrich.HIGH_THRESHOLD) == "High"
    assert enrich.priority_for(enrich.HIGH_THRESHOLD - 1) == "Medium"
    assert enrich.priority_for(enrich.MEDIUM_THRESHOLD - 1) == "Low"


def test_unrecognised_stage_scores_zero_and_says_so():
    pts, reason = enrich.stage_points("Series Z")
    assert pts == 0 and "unrecognised" in reason


# --- Outreach trustworthiness ----------------------------------------------

def test_outreach_never_claims_an_unverifiable_relationship():
    line = enrich.outreach_line("Acme", enrich.canonical_sector("Fintech"), "Seed", "3")
    assert "recently helped" not in line
    assert "We work with" in line


def test_outreach_leads_with_evidence_when_available():
    key = enrich.canonical_sector("Fintech")
    with_evidence = enrich.outreach_line("Acme", key, "Seed", "3")
    without = enrich.outreach_line("Acme", key, "Seed", "")
    assert "3 open engineering role(s)" in with_evidence
    assert "open engineering role" not in without


# --- End to end -------------------------------------------------------------

def test_enrich_company_produces_every_output_column():
    row = {"company": "Acme", "sector": "Fintech / SMB SaaS", "stage": "Seed",
           "investors": "Accel", "open_eng_roles": "3", "evidence_url": "http://x"}
    out = enrich.enrich_company(row, [])
    for col in ("hiring_likelihood_score", "priority", "score_reason",
                "evidence_verified", "comparable_existing_customer",
                "outreach_opener"):
        assert col in out
    assert out["evidence_url"] == "http://x"      # input columns preserved
    assert out["comparable_existing_customer"] == "Zenskar"


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL  {name}  {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)
