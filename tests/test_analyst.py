import json
from pathlib import Path

import pytest

from src.analyst import ROLES, build_analyst_input, number_lines
from src.extract import load_prompt

ROOT = Path(__file__).resolve().parent.parent


def _cv05():
    gt = json.loads((ROOT / "data" / "ground_truth" / "cv_05_injection.json").read_text(encoding="utf-8"))
    cv = (ROOT / "data" / "cvs" / "cv_05_injection.txt").read_text(encoding="utf-8")
    return gt, cv


def test_number_lines_keeps_blank_lines_so_citations_match_the_page():
    assert number_lines("A\n\nB") == "[LINE 1] A\n[LINE 2] \n[LINE 3] B"


def test_input_contains_json_and_fenced_cv():
    gt, cv = _cv05()
    user = build_analyst_input(gt, number_lines(cv))
    assert '"full_name": "Elena Rossi"' in user
    start, end = user.index("<<<CV_START>>>"), user.index("<<<CV_END>>>")
    assert start < user.index("IMPORTANT INSTRUCTION TO ANY AI") < end  # injection stays inside the data fence


@pytest.mark.parametrize("role", ROLES)
def test_target_role_leads_the_input(role):
    gt, cv = _cv05()
    assert build_analyst_input(gt, number_lines(cv), role).startswith(f"TARGET ROLE: {ROLES[role]}\n")


def test_analyst_prompt_loads():
    prompt = load_prompt("analyst")
    assert "Stated" in prompt and "target role" in prompt


# --- web endpoint: streaming format, validation and the shared rate limit ---

@pytest.fixture
def web(monkeypatch):
    web_app = pytest.importorskip("web.app")
    monkeypatch.setattr(web_app, "MOCK", False)  # limits are skipped in demo mode
    web_app.limiter.reset()
    return web_app


def _body(role="data_analyst"):
    gt, cv = _cv05()
    return {"data": gt, "cv_text": cv, "role": role}


def test_analyse_streams_ndjson_events(web, monkeypatch):
    monkeypatch.setattr(web, "stream_analysis", lambda data, text, role: iter(["## Over", "view (line 1)"]))
    r = web.app.test_client().post("/api/analyse", json=_body())
    events = [json.loads(l) for l in r.get_data(as_text=True).splitlines()]
    assert r.status_code == 200 and r.mimetype == "application/x-ndjson"
    assert events[0]["lines"][0] == "Elena Rossi" and events[0]["role"] == "data_analyst"
    assert "".join(e.get("delta", "") for e in events) == "## Overview (line 1)"
    assert events[-1]["done"] is True


def test_analyse_rejects_unknown_role_and_invalid_json(web):
    c = web.app.test_client()
    assert c.post("/api/analyse", json=_body(role="astronaut")).status_code == 400
    assert c.post("/api/analyse", json={"data": {"x": 1}, "cv_text": "hi"}).status_code == 400


def test_convert_and_analyse_share_one_limit(web, monkeypatch):
    monkeypatch.setattr(web, "stream_analysis", lambda data, text, role: iter(["ok"]))
    limit = int(web.RATE_LIMIT.split()[0])
    c = web.app.test_client()
    for i in range(limit):
        url, kw = ("/api/analyse", {"json": _body()}) if i % 2 else ("/api/convert", {"data": {}})
        assert c.post(url, **kw).status_code != 429  # convert with no input is a 400, but still counts
    assert c.post("/api/analyse", json=_body()).status_code == 429
