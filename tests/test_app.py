"""Render the app's results section with a fake result (no API key needed)."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from resumeiq.pipeline import analyse
from tests.test_pipeline import CASE, V3_REPLIES, FakeClient

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_results_render_without_errors():
    result = analyse(CASE["resume"], CASE["jd"], "v3", FakeClient(replies=[dict(r) for r in V3_REPLIES]))
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["result"] = result
    at.run()
    assert not at.exception
    assert any("49/100" in m.value for m in at.metric)
