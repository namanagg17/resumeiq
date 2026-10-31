"""Pipeline tests with a fake model, so they run without an API key.

These check the code paths only. They are NOT evaluation results.
"""

import json

from resumeiq.cases import load_cases
from resumeiq.metrics import score_case
from resumeiq.pipeline import VERSIONS, analyse

CASE = next(c for c in load_cases() if c["id"] == "03_cpp_trap")

V0_TEXT = """**Match Score: 70/100** (approximate)

### Matching Skills:
- Python
- SQL
- C++ programming

### Skill Gaps:
- Data structures knowledge is not shown.
- Web development experience is basic.

### Suggested Improvements:
1. Add a data structures project if true.
"""

SINGLE = {
    "score_breakdown": {"skills": 26, "projects": 24, "problem_solving": 8},
    "score_reasons": {"skills": "x", "projects": "y", "problem_solving": "z"},
    "matches": [
        {"requirement": "Python", "jd_evidence": "Required: Python", "resume_evidence": "Skills: Python"},
        {"requirement": "C++", "jd_evidence": "C++ experience", "resume_evidence": "C++"},
    ],
    "gaps": [{"requirement": "Data structures", "status": "missing", "note": ""}],
    "rewritten_bullets": [{"text": "Built ...", "based_on": "Two academic projects using Python and SQL"}],
    "suggestions": ["Add a web project (only if true)."],
    "ignored_instructions": [],
}

V3_REPLIES = [
    {"skills": [{"name": "Python", "used_in_project": True, "evidence": "Python, C++, SQL"}], "ignored_instructions": []},
    {"role": "dev", "requirements": [], "vague": False, "vague_note": ""},
    {
        "requirements": [
            {"requirement": "Python", "status": "matched", "resume_evidence": "Python, C++, SQL", "jd_evidence": "Python, SQL, data structures"},
            {"requirement": "data structures", "status": "missing", "resume_evidence": "", "jd_evidence": "data structures", "reason": "not shown"},
            {"requirement": "web applications", "status": "partial", "resume_evidence": "basic web development", "jd_evidence": "developing web applications", "reason": "basic only"},
        ],
        "score_breakdown": {"skills": 24, "projects": 20, "problem_solving": 5},
        "score_reasons": {},
    },
    {"rewritten_bullets": [], "suggestions": []},
]


class FakeClient:
    def __init__(self, text="", replies=()):
        self.text, self.replies, self.prompts = text, list(replies), []

    def chat(self, system, user, json_mode=False):
        self.prompts.append(user)
        return self.text

    def chat_json(self, system, user):
        self.prompts.append(user)
        return self.replies.pop(0) if self.replies else json.loads(json.dumps(SINGLE))


def test_v0_parses_free_text_and_flags_cpp():
    result = analyse(CASE["resume"], CASE["jd"], "v0", FakeClient(text=V0_TEXT))
    assert result["score"] == 70
    assert [m["requirement"] for m in result["matches"]] == ["Python", "SQL", "C++ programming"]
    assert result["verification"]["unsupported_matches"] == 1
    metrics = score_case(result, CASE["expected"])
    assert metrics["trap_claims"] == 1


def test_v1_and_v2_compute_total_and_catch_fake_quote():
    for version in ("v1", "v2"):
        client = FakeClient()
        result = analyse(CASE["resume"], CASE["jd"], version, client)
        assert result["score"] == 58
        assert result["verification"]["unsupported_matches"] == 1  # "C++ experience" is not in the JD
        assert CASE["resume"] in client.prompts[0]
        assert "{{" not in client.prompts[0]


def test_v3_chain_shape():
    client = FakeClient(replies=V3_REPLIES)
    result = analyse(CASE["resume"], CASE["jd"], "v3", client)
    assert result["calls"] == 4 and len(client.prompts) == 4
    assert result["score"] == 49
    assert {g["requirement"]: g["status"] for g in result["gaps"]} == {"data structures": "missing", "web applications": "weak"}
    assert result["verification"]["unsupported_matches"] == 0
    metrics = score_case(result, CASE["expected"])
    assert metrics["gaps_found"] == 2 and metrics["trap_claims"] == 0


def test_all_versions_listed():
    assert list(VERSIONS) == ["v0", "v1", "v2", "v3"]
