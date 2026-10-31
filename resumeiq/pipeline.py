"""Run one prompt version and return a result in a common shape.

Every version returns the same keys so the app and the evaluation script
can treat them the same way:

    version, score, breakdown, score_reasons, matches, gaps,
    rewritten_bullets, suggestions, ignored_instructions, verification,
    raw, calls
"""

from __future__ import annotations

import json
import re

from .prompts import load_prompt, render
from .verify import total_score, verify

VERSIONS = {
    "v0": "V0 - Baseline (Milestone 1 prompt, free text)",
    "v1": "V1 - Rubric + JSON output",
    "v2": "V2 - V1 + worked example (few-shot)",
    "v3": "V3 - Prompt chain + verifier",
}


def analyse(resume: str, jd: str, version: str, client) -> dict:
    if version not in VERSIONS:
        raise ValueError(f"Unknown version {version!r}")
    runner = {"v0": _run_v0, "v1": _run_single_json, "v2": _run_single_json, "v3": _run_v3}
    result = runner[version](resume, jd, version, client)
    result["version"] = version
    result["score"] = result.get("score", total_score(result.get("breakdown")))
    result["verification"] = verify(result, resume, jd)
    return result


# ---------------------------------------------------------------- V0

def _run_v0(resume: str, jd: str, version: str, client) -> dict:
    system, user = load_prompt("v0_baseline")
    text = client.chat(system, render(user, resume=resume, jd=jd))
    sections = _split_sections(text)
    score_match = re.search(r"(\d{1,3})\s*/\s*100", text)
    return {
        "score": int(score_match.group(1)) if score_match else None,
        "breakdown": None,
        "score_reasons": {},
        "matches": [{"requirement": item} for item in sections["matches"]],
        "gaps": [{"requirement": item, "status": "missing", "note": ""} for item in sections["gaps"]],
        "rewritten_bullets": [],
        "suggestions": sections["suggestions"],
        "ignored_instructions": [],
        "raw": {"response": text},
        "calls": 1,
    }


def _split_sections(text: str) -> dict:
    """Best-effort parse of the free-text V0 answer into lists."""
    sections = {"matches": [], "gaps": [], "suggestions": []}
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        bullet = re.match(r"^(?:[-*•]|\d+[.)])\s+(.*)", stripped)
        if bullet and current:
            sections[current].append(bullet.group(1).strip("* ").strip())
            continue
        heading = stripped.lower().strip("#* :")
        if "match" in heading and "skill" in heading:
            current = "matches"
        elif any(word in heading for word in ("missing", "gap", "insufficient")):
            current = "gaps"
        elif any(word in heading for word in ("improve", "suggest")):
            current = "suggestions"
        elif stripped.startswith("#") or stripped.endswith(":"):
            current = None
    return sections


# ---------------------------------------------------------------- V1 / V2

def _run_single_json(resume: str, jd: str, version: str, client) -> dict:
    name = "v1_rubric" if version == "v1" else "v2_fewshot"
    system, user = load_prompt(name)
    data = client.chat_json(system, render(user, resume=resume, jd=jd))
    return {
        "breakdown": data.get("score_breakdown"),
        "score_reasons": data.get("score_reasons", {}),
        "matches": _list(data.get("matches")),
        "gaps": _list(data.get("gaps")),
        "rewritten_bullets": _list(data.get("rewritten_bullets")),
        "suggestions": _list(data.get("suggestions")),
        "ignored_instructions": _list(data.get("ignored_instructions")),
        "raw": data,
        "calls": 1,
    }


# ---------------------------------------------------------------- V3

def _run_v3(resume: str, jd: str, version: str, client) -> dict:
    # Step 1a: pull facts out of the resume (with exact quotes)
    system, user = load_prompt("v3/extract_resume")
    facts = client.chat_json(system, render(user, resume=resume))

    # Step 1b: pull requirements out of the job description
    system, user = load_prompt("v3/extract_jd")
    requirements = client.chat_json(system, render(user, jd=jd))

    # Step 2: score requirement by requirement, using only the extracted facts
    system, user = load_prompt("v3/score")
    scored = client.chat_json(
        system,
        render(user, facts=_dump(facts), requirements=_dump(requirements)),
    )

    reqs = _list(scored.get("requirements"))
    matches = [r for r in reqs if r.get("status") in ("matched", "partial")]
    gaps = [
        {
            "requirement": r.get("requirement", ""),
            "status": "weak" if r.get("status") == "partial" else "missing",
            "note": r.get("reason", ""),
        }
        for r in reqs
        if r.get("status") in ("partial", "missing")
    ]

    # Step 3: rewrite bullets from facts only
    system, user = load_prompt("v3/rewrite")
    rewrite = client.chat_json(system, render(user, facts=_dump(facts), gaps=_dump(gaps)))

    return {
        "breakdown": scored.get("score_breakdown"),
        "score_reasons": scored.get("score_reasons", {}),
        "matches": matches,
        "gaps": gaps,
        "rewritten_bullets": _list(rewrite.get("rewritten_bullets")),
        "suggestions": _list(rewrite.get("suggestions")),
        "ignored_instructions": _list(facts.get("ignored_instructions")),
        "jd_is_vague": bool(requirements.get("vague")),
        "raw": {"facts": facts, "requirements": requirements, "scored": scored, "rewrite": rewrite},
        "calls": 4,
    }


def _list(value) -> list:
    return value if isinstance(value, list) else []


def _dump(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)
