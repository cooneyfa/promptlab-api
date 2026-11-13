"""End-to-end API tests for PromptLab (hermetic: in-memory SQLite)."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client():
    app = create_app(db_path=":memory:")
    with TestClient(app) as c:
        yield c


def _make(client, name="summarizer", template="Summarize this: {text}"):
    r = client.post(
        "/prompts",
        json={"name": name, "template": template, "description": "test prompt"},
    )
    assert r.status_code == 201, r.text
    return r.json()


# -- health ---------------------------------------------------------------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# -- CRUD -----------------------------------------------------------------

def test_create_prompt_returns_version_1(client):
    p = _make(client)
    assert p["version"] == 1
    assert p["name"] == "summarizer"


def test_create_duplicate_name_conflicts(client):
    _make(client, name="dup")
    r = client.post("/prompts", json={"name": "dup", "template": "hi {x}"})
    assert r.status_code == 409


def test_create_rejects_blank_template(client):
    r = client.post("/prompts", json={"name": "bad", "template": ""})
    assert r.status_code == 422


def test_get_prompt(client):
    p = _make(client)
    r = client.get(f"/prompts/{p['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == p["id"]


def test_get_missing_prompt_404(client):
    assert client.get("/prompts/9999").status_code == 404


def test_list_prompts(client):
    _make(client, name="a")
    _make(client, name="b", template="other {x}")
    r = client.get("/prompts")
    assert r.status_code == 200
    assert {p["name"] for p in r.json()} == {"a", "b"}


def test_update_creates_new_version(client):
    p = _make(client)
    r = client.put(
        f"/prompts/{p['id']}",
        json={"template": "Summarize briefly: {text}", "description": "v2"},
    )
    assert r.status_code == 200
    assert r.json()["version"] == 2
    versions = client.get(f"/prompts/{p['id']}/versions").json()
    assert [v["version"] for v in versions] == [1, 2]
    assert versions[0]["template"] == "Summarize this: {text}"


def test_update_missing_prompt_404(client):
    r = client.put("/prompts/9999", json={"template": "x {y}"})
    assert r.status_code == 404


def test_delete_prompt(client):
    p = _make(client)
    assert client.delete(f"/prompts/{p['id']}").status_code == 204
    assert client.get(f"/prompts/{p['id']}").status_code == 404


def test_delete_missing_prompt_404(client):
    assert client.delete("/prompts/9999").status_code == 404


# -- render ---------------------------------------------------------------

def test_render_fills_variables(client):
    p = _make(client)
    r = client.post(f"/prompts/{p['id']}/render", json={"variables": {"text": "hello"}})
    assert r.status_code == 200
    assert r.json()["rendered"] == "Summarize this: hello"


def test_render_missing_variable_422(client):
    p = _make(client)
    r = client.post(f"/prompts/{p['id']}/render", json={"variables": {}})
    assert r.status_code == 422
    assert "text" in r.json()["detail"]


def test_render_uses_latest_version(client):
    p = _make(client)
    client.put(f"/prompts/{p['id']}", json={"template": "TL;DR: {text}"})
    r = client.post(f"/prompts/{p['id']}/render", json={"variables": {"text": "abc"}})
    assert r.json()["rendered"] == "TL;DR: abc"


# -- evaluate -------------------------------------------------------------

def test_evaluate_scores_structure(client):
    r = client.post(
        "/evaluate",
        json={"text": 'Summarize the following article in 3 bullet points:\n- "{article}"'},
    )
    assert r.status_code == 200
    body = r.json()
    assert set(body["scores"]) == {"length", "specificity", "formatting"}
    assert all(0.0 <= s <= 1.0 for s in body["scores"].values())
    assert 0.0 <= body["overall"] <= 100.0
    assert len(body["notes"]) == 3


def test_evaluate_prefers_specific_over_vague(client):
    vague = client.post("/evaluate", json={"text": "do stuff with this thing ok"}).json()
    specific = client.post(
        "/evaluate",
        json={"text": "Summarize the report in exactly 5 bullet points. Quote \"revenue\" figures."},
    ).json()
    assert specific["overall"] > vague["overall"]


def test_evaluate_is_deterministic(client):
    text = "Explain {topic} to a beginner in under 200 words."
    a = client.post("/evaluate", json={"text": text}).json()
    b = client.post("/evaluate", json={"text": text}).json()
    assert a == b


def test_evaluate_rejects_empty(client):
    assert client.post("/evaluate", json={"text": ""}).status_code == 422
