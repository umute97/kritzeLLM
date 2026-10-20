import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kritzellm.api.app import render_openapi

SPEC_PATH = Path(__file__).resolve().parents[2] / "api" / "openapi.json"

JOURNAL_ID = "jrn_01k7c8x2v4f6g8h9j0k1m2n3p4"
CONVERSATION_ID = "cnv_01k7cbc5d7f9g1h3j5k7m9n1p3"
JOB_ID = "job_01k7c9a4c6e8g0h2j4k6m8n0p2"


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()


def _without_version(spec: str) -> dict:
    data = json.loads(spec)
    data["info"].pop("version", None)
    return data


def test_committed_spec_matches_the_code() -> None:
    """api/openapi.json must be regenerated (`just api-export`) whenever the API changes."""
    assert SPEC_PATH.exists(), "api/openapi.json is missing. Run `just api-export`."
    # The version is stamped by release-please, so it may run ahead of the installed package.
    assert _without_version(SPEC_PATH.read_text()) == _without_version(render_openapi()), (
        "api/openapi.json is out of date. Run `just api-export`."
    )


def test_spec_writes_whole_numbers_like_javascript() -> None:
    """release-please rewrites the spec with JSON.stringify, which writes `1.0` as `1`."""
    assert not re.search(r":\s-?\d+\.0\b", render_openapi())


# Every designed operation that still answers 501.
STUB_CASES = [
    ("POST", f"/journals/{JOURNAL_ID}/exports", {"format": "markdown"}),
    ("GET", "/search?q=lisbon", None),
    ("GET", "/conversations", None),
    ("POST", "/conversations", None),
    ("GET", f"/conversations/{CONVERSATION_ID}", None),
    ("PATCH", f"/conversations/{CONVERSATION_ID}", {"title": "Lisbon"}),
    ("DELETE", f"/conversations/{CONVERSATION_ID}", None),
    ("POST", f"/conversations/{CONVERSATION_ID}/messages", {"content": "hi"}),
    ("GET", f"/jobs/{JOB_ID}/result", None),
    ("POST", "/admin/reindex", None),
]


@pytest.mark.parametrize(("method", "path", "body"), STUB_CASES)
def test_stubs_answer_501_problem(
    client: TestClient, method: str, path: str, body: dict | None
) -> None:
    response = client.request(method, path, json=body)
    assert response.status_code == 501
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Not Implemented"


# Operations that do real work now; they have their own tests.
BUILT = {
    "getHealth",
    "listJournals",
    "createJournal",
    "getJournal",
    "updateJournal",
    "deleteJournal",
    "uploadPages",
    "listPages",
    "getPage",
    "updatePage",
    "deletePage",
    "getPageImage",
    "replacePageBlocks",
    "transcribePage",
    "getBlock",
    "updateBlock",
    "listJobs",
    "getJob",
}


def test_every_operation_is_built_or_has_a_stub_test() -> None:
    spec = json.loads(render_openapi())
    operation_ids = {
        op["operationId"] for methods in spec["paths"].values() for op in methods.values()
    }
    assert operation_ids >= BUILT
    assert len(STUB_CASES) == len(operation_ids) - len(BUILT)


def test_malformed_ids_are_422_problems(client: TestClient) -> None:
    response = client.get("/pages/not-a-page-id")
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert [error["parameter"] for error in response.json()["errors"]] == ["pageId"]


def test_invalid_query_values_name_the_parameter(client: TestClient) -> None:
    response = client.get("/pages?journalId=nope&limit=0")
    assert response.status_code == 422
    assert {error["parameter"] for error in response.json()["errors"]} == {"journalId", "limit"}


def test_invalid_body_fields_point_at_the_field(client: TestClient) -> None:
    response = client.post("/journals", json={"name": "", "nope": 1})
    assert response.status_code == 422
    pointers = {error["pointer"] for error in response.json()["errors"]}
    assert pointers == {"/name", "/nope"}


def test_malformed_json_is_400(client: TestClient) -> None:
    response = client.post(
        "/journals", content=b"{not json", headers={"content-type": "application/json"}
    )
    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"


def test_unknown_routes_are_404_problems(client: TestClient) -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"


def test_repeated_query_parameters_are_422(client: TestClient) -> None:
    response = client.get("/pages?limit=5&limit=50")
    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"detail": "Give this parameter only once", "parameter": "limit"}
    ]


def test_paths_outside_the_api_are_404_problems(client: TestClient) -> None:
    response = client.get("http://test/nope%0A")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"


def test_unknown_query_parameters_are_422(client: TestClient) -> None:
    response = client.get("/pages?limt=5")
    assert response.status_code == 422
    assert response.json()["errors"] == [{"detail": "Unknown query parameter", "parameter": "limt"}]


@pytest.mark.parametrize(
    ("path", "allow"),
    [
        ("/journals", "GET, POST"),
        (f"/journals/{JOURNAL_ID}", "DELETE, GET, PATCH"),
        ("/health", "GET"),
    ],
)
def test_405_lists_every_allowed_method(client: TestClient, path: str, allow: str) -> None:
    response = client.request("TRACE", path)
    assert response.status_code == 405
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["allow"] == allow
