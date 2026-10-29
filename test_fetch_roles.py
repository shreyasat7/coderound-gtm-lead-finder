"""
Tests for the job-board API layer.

These never touch the network. They test the two things that actually decide
whether a count is right: how each provider's JSON is read, and what counts
as an engineering role. The sample payloads below are trimmed copies of real
responses (see roles_cache.json for the live data).

Run:  python3 test_fetch_roles.py      or      pytest -q
"""

import fetch_roles as fr


# --- what counts as an engineering hire -------------------------------------

def test_obvious_engineering_titles_count():
    for title in ("Senior Software Engineer", "Backend Developer",
                  "Data Scientist - Evaluations", "Infrastructure Engineer",
                  "iOS Engineer", "Site Reliability Engineer"):
        assert fr.is_engineering_role(title), title


def test_gtm_roles_with_engineer_in_the_title_do_not_count():
    """CodeRound screens software engineers. A Sales Engineer is a GTM hire -
    counting it would inflate the strongest signal in the score."""
    for title in ("Sales Engineer", "Solutions Engineer",
                  "Customer Engineer", "Support Engineer"):
        assert not fr.is_engineering_role(title), title


def test_clearly_non_engineering_titles_do_not_count():
    for title in ("Engagement Manager", "Accounts Payable Manager",
                  "Area Collections Manager", "Recruiter"):
        assert not fr.is_engineering_role(title), title


def test_department_breaks_the_tie_when_the_title_is_ambiguous():
    """Ashby uses titles like 'Member of Technical Staff' that say nothing on
    their own, but carry a department."""
    assert not fr.is_engineering_role("Member of Technical Staff")
    assert fr.is_engineering_role("Member of Technical Staff", "Engineering")


def test_missing_or_empty_input_is_safe():
    assert not fr.is_engineering_role("", "")
    assert not fr.is_engineering_role(None, None)


# --- reading each provider's JSON -------------------------------------------

GREENHOUSE = {"jobs": [{"title": "Software Engineer"}, {"title": "Recruiter"}]}
ASHBY = {"jobs": [{"title": "Engagement Manager", "department": "Business Development"},
                  {"title": "Embedded Infrastructure Engineer", "department": "Engineering"}]}
LEVER = [{"text": "accounts payable manager", "categories": {"team": "finance"}},
         {"text": "Senior Backend Engineer", "categories": {"team": "engineering"}}]


def test_each_provider_is_read_into_the_same_shape():
    for provider, payload in (("greenhouse", GREENHOUSE), ("ashby", ASHBY), ("lever", LEVER)):
        postings = fr.extract_postings(provider, payload)
        assert len(postings) == 2, provider
        assert all(isinstance(t, str) for t, _ in postings), provider


def test_counts_only_the_engineering_postings():
    for provider, payload in (("greenhouse", GREENHOUSE), ("ashby", ASHBY), ("lever", LEVER)):
        postings = fr.extract_postings(provider, payload)
        eng = [t for t, d in postings if fr.is_engineering_role(t, d)]
        assert len(eng) == 1, f"{provider}: {eng}"


def test_unknown_provider_is_rejected_loudly():
    try:
        fr.extract_postings("workday", {})
    except ValueError:
        return
    assert False, "an unsupported provider must raise, not return 0 silently"


def test_empty_board_is_zero_not_an_error():
    assert fr.extract_postings("greenhouse", {"jobs": []}) == []


def test_unsupported_provider_fails_without_a_network_call():
    result = fr.fetch_board("workday", "anything")
    assert result["ok"] is False and "unsupported" in result["error"]


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn(); print(f"  PASS  {name}")
        except AssertionError as exc:
            failed += 1; print(f"  FAIL  {name}  {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)
