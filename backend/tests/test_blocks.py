from collections.abc import Callable

import pytest
from conftest import FakeVisionModel, get_job, get_page, new_journal, upload
from fastapi.testclient import TestClient

from kritzellm.ids import Prefix, new_id

pytestmark = pytest.mark.db

MakeImage = Callable[..., bytes]

PAGE = {
    "page_label": None,
    "entry_dates": ["2026-03-14"],
    "blocks": [
        {"kind": "heading", "text": "14. März", "uncertain": False},
        {"kind": "paragraph", "text": "Endlich beim Arzt gewesen.", "uncertain": False},
        {"kind": "marginNote", "text": "anrufen [?]", "uncertain": True},
    ],
}


def _patch(client: TestClient, block_id: str, **changes: object) -> dict:
    response = client.patch(f"/blocks/{block_id}", json=changes)
    assert response.status_code == 200, response.text
    return response.json()


def _put(client: TestClient, page_id: str, blocks: list[dict]) -> dict:
    response = client.put(f"/pages/{page_id}/blocks", json={"blocks": blocks})
    assert response.status_code == 200, response.text
    return response.json()


def _texts(blocks: list[dict]) -> list[tuple[int, str]]:
    return [(block["seq"], block["text"]) for block in blocks]


@pytest.fixture
def page(
    db_client: TestClient,
    make_image: MakeImage,
    work: Callable[[], None],
    vision_model: FakeVisionModel,
) -> dict:
    """A page the worker read into PAGE's three blocks."""
    vision_model.outputs = [PAGE]
    item = upload(db_client, new_journal(db_client), make_image())[0]
    work()
    return get_page(db_client, item["page"]["id"])


def test_get_block(db_client: TestClient, page: dict) -> None:
    block = page["blocks"][1]

    response = db_client.get(f"/blocks/{block['id']}")

    assert response.status_code == 200, response.text
    assert response.json() == block


def test_unknown_block_is_404(db_client: TestClient) -> None:
    unknown = new_id(Prefix.BLOCK)
    for response in (
        db_client.get(f"/blocks/{unknown}"),
        db_client.patch(f"/blocks/{unknown}", json={"text": "x"}),
    ):
        assert response.status_code == 404
        assert response.json()["detail"] == "Block not found."


def test_patch_changes_only_the_given_fields(db_client: TestClient, page: dict) -> None:
    block = page["blocks"][2]

    result = _patch(db_client, block["id"], text="anrufen Mama")

    assert result["block"] == {**block, "text": "anrufen Mama"}
    job = result["job"]
    assert (job["kind"], job["status"]) == ("reindexPage", "queued")
    assert job["target"] == {"type": "page", "id": page["id"]}
    fixed = get_page(db_client, page["id"])
    assert fixed["blocks"][2] == result["block"]
    assert fixed["updatedAt"] > page["updatedAt"]

    result = _patch(db_client, block["id"], uncertain=False, kind="paragraph")
    assert result["block"] == {
        **block,
        "text": "anrufen Mama",
        "uncertain": False,
        "kind": "paragraph",
    }


def test_null_is_no_correction(db_client: TestClient, page: dict) -> None:
    response = db_client.patch(f"/blocks/{page['blocks'][0]['id']}", json={"text": None})

    assert response.status_code == 422
    assert [error["pointer"] for error in response.json()["errors"]] == ["/text"]


def test_edits_in_a_row_share_the_queued_reindex(
    db_client: TestClient, page: dict, work: Callable[[], None]
) -> None:
    first, second = page["blocks"][:2]
    job = _patch(db_client, first["id"], text="15. März")["job"]
    assert _patch(db_client, second["id"], text="Beim Arzt.")["job"]["id"] == job["id"]
    replaced = _put(db_client, page["id"], [{"kind": "paragraph", "text": "Alles neu."}])
    assert replaced["job"]["id"] == job["id"]

    work()

    done = get_job(db_client, job["id"])
    assert (done["status"], done["progress"]) == ("succeeded", {"done": 1, "total": 1})
    fixed = get_page(db_client, page["id"])
    assert (fixed["status"], fixed["error"]) == ("ready", None)
    assert _texts(fixed["blocks"]) == [(0, "Alles neu.")]
    # That job is done, so the next edit gets a new one.
    later = _patch(db_client, fixed["blocks"][0]["id"], text="Doch nicht.")
    assert later["job"]["id"] != job["id"]


def test_put_reorders_keeps_creates_and_deletes(db_client: TestClient, page: dict) -> None:
    heading, paragraph, note = page["blocks"]

    result = _put(
        db_client,
        page["id"],
        [
            {"id": note["id"], "kind": "marginNote", "text": "anrufen!"},
            {"kind": "list", "text": "Brot\nMilch"},
            {"id": heading["id"], "kind": "heading", "text": "14. März"},
        ],
    )

    blocks = result["blocks"]
    assert _texts(blocks) == [(0, "anrufen!"), (1, "Brot\nMilch"), (2, "14. März")]
    assert blocks[0]["id"] == note["id"]
    assert blocks[0]["uncertain"] is False  # Left out, so back to the default.
    assert blocks[1]["id"].startswith("blk_")
    assert blocks[1]["id"] not in {heading["id"], paragraph["id"], note["id"]}
    assert blocks[2]["id"] == heading["id"]
    assert all(block["pageId"] == page["id"] for block in blocks)
    assert result["job"]["kind"] == "reindexPage"
    assert get_page(db_client, page["id"])["blocks"] == blocks
    assert db_client.get(f"/blocks/{paragraph['id']}").status_code == 404


def test_put_nothing_clears_the_page(db_client: TestClient, page: dict) -> None:
    assert _put(db_client, page["id"], [])["blocks"] == []
    assert get_page(db_client, page["id"])["blocks"] == []


def test_put_rejects_foreign_and_repeated_ids(
    db_client: TestClient, page: dict, make_image: MakeImage, work: Callable[[], None]
) -> None:
    other = upload(db_client, new_journal(db_client), make_image(color="blue"))[0]
    work()
    foreign = get_page(db_client, other["page"]["id"])["blocks"][0]["id"]
    mine = page["blocks"][0]["id"]

    response = db_client.put(
        f"/pages/{page['id']}/blocks",
        json={
            "blocks": [
                {"id": mine, "kind": "heading", "text": "a"},
                {"id": mine, "kind": "heading", "text": "b"},
                {"id": foreign, "kind": "heading", "text": "c"},
                {"id": new_id(Prefix.BLOCK), "kind": "heading", "text": "d"},
            ]
        },
    )

    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"detail": "This block is given more than once", "pointer": "/blocks/1/id"},
        {"detail": "Not a block of this page", "pointer": "/blocks/2/id"},
        {"detail": "Not a block of this page", "pointer": "/blocks/3/id"},
    ]
    assert get_page(db_client, page["id"])["blocks"] == page["blocks"]


def test_unknown_page_is_404(db_client: TestClient) -> None:
    unknown = new_id(Prefix.PAGE)
    for response in (
        db_client.put(f"/pages/{unknown}/blocks", json={"blocks": []}),
        db_client.post(f"/pages/{unknown}/transcribe"),
    ):
        assert response.status_code == 404
        assert response.json()["detail"] == "Page not found."


def test_transcribing_again_reads_the_page_afresh(
    db_client: TestClient, page: dict, work: Callable[[], None], vision_model: FakeVisionModel
) -> None:
    vision_model.outputs = [
        {**PAGE, "blocks": [{"kind": "other", "text": "Neu", "uncertain": False}]}
    ]

    response = db_client.post(f"/pages/{page['id']}/transcribe")

    assert response.status_code == 202, response.text
    job = response.json()
    assert (job["kind"], job["status"]) == ("transcribePage", "queued")
    assert job["target"] == {"type": "page", "id": page["id"]}
    assert response.headers["location"] == f"/api/v1/jobs/{job['id']}"

    work()

    done = get_job(db_client, job["id"])
    assert (done["status"], done["progress"]) == ("succeeded", {"done": 2, "total": 2})
    read = get_page(db_client, page["id"])
    assert read["status"] == "ready"
    assert _texts(read["blocks"]) == [(0, "Neu")]
    assert db_client.get(f"/blocks/{page['blocks'][0]['id']}").status_code == 404


def test_a_page_waiting_to_be_read_cannot_be_changed(
    db_client: TestClient, page: dict, make_image: MakeImage
) -> None:
    unread = upload(db_client, new_journal(db_client), make_image(color="green"))[0]["page"]["id"]
    assert db_client.post(f"/pages/{page['id']}/transcribe").status_code == 202

    for response in (
        db_client.put(f"/pages/{unread}/blocks", json={"blocks": []}),
        db_client.post(f"/pages/{unread}/transcribe"),
        db_client.patch(f"/blocks/{page['blocks'][0]['id']}", json={"text": "x"}),
        db_client.put(f"/pages/{page['id']}/blocks", json={"blocks": []}),
        db_client.post(f"/pages/{page['id']}/transcribe"),
    ):
        assert response.status_code == 409, response.text
        assert response.headers["content-type"] == "application/problem+json"
    assert get_page(db_client, page["id"])["blocks"] == page["blocks"]


def test_a_failed_page_can_be_typed_up_by_hand(
    db_client: TestClient,
    make_image: MakeImage,
    work: Callable[[], None],
    vision_model: FakeVisionModel,
) -> None:
    vision_model.outputs = [{**PAGE, "entry_dates": ["someday"]}]
    page_id = upload(db_client, new_journal(db_client), make_image(color="brown"))[0]["page"]["id"]
    work()
    assert get_page(db_client, page_id)["status"] == "failed"

    _put(db_client, page_id, [{"kind": "paragraph", "text": "Selbst abgetippt."}])
    work()

    page = get_page(db_client, page_id)
    assert (page["status"], page["error"]) == ("ready", None)
    assert _texts(page["blocks"]) == [(0, "Selbst abgetippt.")]


def test_deleting_a_page_deletes_its_reindex_job(db_client: TestClient, page: dict) -> None:
    job = _patch(db_client, page["blocks"][0]["id"], text="x")["job"]

    assert db_client.delete(f"/pages/{page['id']}").status_code == 204
    assert db_client.get(f"/jobs/{job['id']}").status_code == 404
