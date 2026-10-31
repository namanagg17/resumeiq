"""Turn one result + the case's expected answer into numbers for the eval table."""

from __future__ import annotations

from .verify import term_in


def score_case(result: dict, expected: dict) -> dict:
    score = result.get("score")
    low, high = expected.get("score_range", [0, 100])

    gap_text = " ".join(
        f"{g.get('requirement', '')} {g.get('note', '')}" for g in result.get("gaps", [])
    )
    expected_missing = expected.get("expected_missing", [])
    found = [term for term in expected_missing if term_in(term, gap_text)]

    claimed_text = [
        f"{m.get('requirement', '')} {m.get('jd_evidence', '')}" for m in result.get("matches", [])
    ]
    traps = [
        term for term in expected.get("must_not_claim", [])
        if any(term_in(term, text) for text in claimed_text)
    ]

    verification = result.get("verification", {})
    return {
        "score": score,
        "score_in_range": score is not None and low <= score <= high,
        "gaps_found": len(found),
        "gaps_expected": len(expected_missing),
        "gap_recall": round(len(found) / len(expected_missing), 2) if expected_missing else None,
        "trap_claims": len(traps),
        "trap_terms": "; ".join(traps),
        "unsupported_matches": verification.get("unsupported_matches", 0),
        "matches_checked": verification.get("matches_checked", 0),
        "score_issues": "; ".join(verification.get("score_issues", [])),
    }
