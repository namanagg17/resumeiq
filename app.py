"""ResumeIQ web app. Run with:  streamlit run app.py"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from resumeiq.cases import load_cases
from resumeiq.llm import ConfigError, LLMClient, load_config
from resumeiq.pipeline import VERSIONS, analyse

load_dotenv()
st.set_page_config(page_title="ResumeIQ", layout="wide")

st.title("ResumeIQ")
st.caption(
    "Compare a resume with a job description: rubric-based match score, skill gaps "
    "and resume bullets that never invent experience."
)
st.warning("Use made-up or anonymised resumes only. Do not paste real personal data.")

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Settings")
    version = st.radio(
        "Prompt version",
        list(VERSIONS),
        index=3,
        format_func=lambda v: VERSIONS[v],
    )
    cases = load_cases()
    sample = st.selectbox(
        "Load a test case",
        ["(none)"] + [c["id"] for c in cases],
    )
    if st.button("Load sample") and sample != "(none)":
        case = next(c for c in cases if c["id"] == sample)
        st.session_state["resume"] = case["resume"]
        st.session_state["jd"] = case["jd"]

# ---------------------------------------------------------------- inputs
left, right = st.columns(2)
resume = left.text_area("Resume (plain text)", height=280, key="resume")
jd = right.text_area("Job description", height=280, key="jd")

if st.button("Analyse", type="primary", disabled=not (resume.strip() and jd.strip())):
    try:
        client = LLMClient(load_config())
    except ConfigError as error:
        st.error(str(error))
        st.stop()
    with st.spinner(f"Running {VERSIONS[version]} ..."):
        try:
            st.session_state["result"] = analyse(resume, jd, version, client)
        except Exception as error:
            st.error(f"Analysis failed: {error}")
            st.stop()

result = st.session_state.get("result")
if not result:
    st.stop()

# ---------------------------------------------------------------- results
st.divider()
st.subheader(f"Result  ·  {VERSIONS[result['version']]}")

score_col, breakdown_col = st.columns([1, 2])
score = result.get("score")
score_col.metric("Match score", f"{score}/100" if score is not None else "n/a")
score_col.caption("Approximate, rubric-based. Not a hiring decision.")

breakdown = result.get("breakdown") or {}
reasons = result.get("score_reasons") or {}
for part, maximum in (("skills", 40), ("projects", 40), ("problem_solving", 20)):
    value = breakdown.get(part)
    if isinstance(value, (int, float)):
        breakdown_col.progress(
            min(max(value / maximum, 0.0), 1.0),
            text=f"{part.replace('_', ' ').title()}: {value}/{maximum} — {reasons.get(part, '')}",
        )

verification = result.get("verification", {})
if verification.get("unsupported_matches"):
    st.error(
        f"Verifier: {verification['unsupported_matches']} of {verification['matches_checked']} "
        "claimed matches could not be found in the resume or job description."
    )
elif verification.get("matches_checked"):
    st.success(f"Verifier: all {verification['matches_checked']} claimed matches are backed by the text.")
for issue in verification.get("score_issues", []):
    st.warning(f"Score check: {issue}")
if result.get("ignored_instructions"):
    st.warning("Ignored instructions found in the input: " + "; ".join(map(str, result["ignored_instructions"])))
if result.get("jd_is_vague"):
    st.info("The job description is vague, so the score is less reliable.")

match_col, gap_col = st.columns(2)
with match_col:
    st.markdown("#### Matching requirements")
    for match in result.get("matches", []):
        mark = "✅" if match.get("verified") else "⚠️"
        status = f" ({match['status']})" if match.get("status") else ""
        st.markdown(f"{mark} **{match.get('requirement', '')}**{status}")
        if match.get("resume_evidence"):
            st.caption(f"Resume: “{match['resume_evidence']}”")
        for problem in match.get("problems", []):
            st.caption(f"⚠️ {problem}")
with gap_col:
    st.markdown("#### Gaps")
    for gap in result.get("gaps", []):
        st.markdown(f"- **{gap.get('requirement', '')}** · {gap.get('status', '')}  \n  {gap.get('note', '')}")

st.markdown("#### Rewritten bullets (suggestions)")
for bullet in result.get("rewritten_bullets", []):
    st.markdown(f"- {bullet.get('text', '')}")
    if bullet.get("based_on"):
        st.caption(f"Based on resume: “{bullet['based_on']}”")

st.markdown("#### Other suggestions")
for suggestion in result.get("suggestions", []):
    st.markdown(f"- {suggestion}")

with st.expander("Raw model output"):
    st.json(result.get("raw", {}))
