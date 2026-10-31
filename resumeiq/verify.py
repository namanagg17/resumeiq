"""Deterministic checks on model output. No LLM calls here.

The main check: every match the model claims must be backed by text that
really appears in the resume AND in the job description. This catches
invented skills and skills the job never asked for (e.g. the C++ case).
"""

from __future__ import annotations

import re

SCORE_MAX = {"skills": 40, "projects": 40, "problem_solving": 20}

STOPWORDS = {
    "a", "an", "and", "the", "of", "in", "on", "for", "with", "to", "or",
    "skill", "skills", "experience", "knowledge", "basic", "level", "only",
    "programming", "using", "strong", "good",
}


def normalize(text: str) -> str:
    """Lowercase, unify quotes/dashes, drop punctuation except + and #."""
    text = text.lower()
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"[^a-z0-9+#\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> list[str]:
    return [t for t in normalize(text).split() if t not in STOPWORDS]


def quote_in(quote: str, source: str) -> bool:
    """True if the quote appears in the source, ignoring case and punctuation.

    A quote with "..." is split and each part must appear.
    """
    parts = [p for p in re.split(r"\.\.\.|…", quote) if normalize(p)]
    if not parts:
        return False
    padded = f" {normalize(source)} "
    return all(f" {normalize(p)} " in padded for p in parts)


def term_in(term: str, source: str) -> bool:
    """True if every meaningful word of a short term appears in the source."""
    words = tokens(re.sub(r"\(.*?\)", " ", term))
    if not words:
        return False
    source_words = set(normalize(source).split())
    return all(w in source_words for w in words)


def check_match(match: dict, resume: str, jd: str) -> list[str]:
    """Return a list of problems with one claimed match (empty = verified)."""
    problems = []
    requirement = match.get("requirement", "")
    resume_ev = (match.get("resume_evidence") or "").strip()
    jd_ev = (match.get("jd_evidence") or "").strip()

    if resume_ev:
        if not quote_in(resume_ev, resume):
            problems.append("resume quote not found in resume")
    elif not term_in(requirement, resume):
        problems.append("skill not found in resume")

    if jd_ev:
        if not quote_in(jd_ev, jd):
            problems.append("job-description quote not found in job description")
    elif not term_in(requirement, jd):
        problems.append("job description does not ask for this")
    return problems


def check_score(breakdown: dict | None) -> list[str]:
    if breakdown is None:
        return ["no score breakdown"]
    problems = []
    for part, maximum in SCORE_MAX.items():
        value = breakdown.get(part)
        if not isinstance(value, (int, float)):
            problems.append(f"{part} score missing")
        elif not 0 <= value <= maximum:
            problems.append(f"{part} score {value} is outside 0-{maximum}")
    return problems


def total_score(breakdown: dict | None) -> int | None:
    """Add the rubric parts in code (never trust the model's arithmetic)."""
    if not breakdown:
        return None
    total = 0
    for part, maximum in SCORE_MAX.items():
        value = breakdown.get(part)
        if not isinstance(value, (int, float)):
            return None
        total += max(0, min(maximum, value))
    return round(total)


def verify(result: dict, resume: str, jd: str) -> dict:
    """Mark each match verified/unverified and collect issues."""
    unsupported = 0
    for match in result.get("matches", []):
        problems = check_match(match, resume, jd)
        match["verified"] = not problems
        match["problems"] = problems
        if problems:
            unsupported += 1

    issues = [] if result["version"] == "v0" else check_score(result.get("breakdown"))
    return {
        "matches_checked": len(result.get("matches", [])),
        "unsupported_matches": unsupported,
        "score_issues": issues,
    }
