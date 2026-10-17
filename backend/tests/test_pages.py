import io
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from kritzellm.api.routes.journals import MAX_FILE_BYTES
from kritzellm.ids import Prefix, new_id

pytestmark = pytest.mark.db

MakeImage = Callable[..., bytes]


def _journal(client: TestClient, name: str = "Pages") -> str:
    response = client.post("/journals", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _upload(client: TestClient, journal_id: str, *files: tuple[str, bytes], **form: object) -> dict:
    response = _post(client, journal_id, *files, **form)
    assert response.status_code == 201, response.text
    return response.json()


def _post(client: TestClient, journal_id: str, *files: tuple[str, bytes], **form: object):
    return client.post(
        f"/journals/{journal_id}/pages",
        files=[("files", (name, data, "application/octet-stream")) for name, data in files],
        data={key: str(value) for key, value in form.items()},
    )


def _image(client: TestClient, page: dict, variant: str):
    response = client.get(page["image"]["urls"][variant].removeprefix("/api/v1"))
    assert response.status_code == 200, response.text
    return response


def _files(data_dir: Path) -> list[str]:
    return sorted(str(path.relative_to(data_dir)) for path in data_dir.rglob("*") if path.is_file())


def test_upload_stores_and_serves_three_variants(
    db_client: TestClient, make_image: MakeImage, data_dir: Path
) -> None:
    journal_id = _journal(db_client)
    sideways = make_image(size=(3000, 2000), orientation=6)
    heic = make_image("HEIF", size=(200, 100), color="blue")

    items = _upload(db_client, journal_id, ("p1.jpg", sideways), ("p2.heic", heic))["items"]

    assert [item["filename"] for item in items] == ["p1.jpg", "p2.heic"]
    assert [item["duplicate"] for item in items] == [False, False]
    assert [item["job"]["kind"] for item in items] == ["ingestPage", "ingestPage"]
    first, second = (item["page"] for item in items)
    assert first["id"].startswith("pg_")
    assert (first["pageNumber"], second["pageNumber"]) == (1, 2)
    assert first["status"] == "uploaded"
    assert first["entryDates"] == []
    assert first["image"]["width"] == 1365
    assert first["image"]["height"] == 2048
    assert first["image"]["urls"]["thumbnail"] == (
        f"/api/v1/pages/{first['id']}/image?variant=thumbnail"
    )

    original = _image(db_client, first, "original")
    assert original.content == sideways
    assert original.headers["content-type"] == "image/jpeg"
    assert "immutable" in original.headers["cache-control"]
    normalized = _image(db_client, first, "normalized")
    assert Image.open(io.BytesIO(normalized.content)).size == (1365, 2048)
    thumbnail = _image(db_client, first, "thumbnail")
    assert Image.open(io.BytesIO(thumbnail.content)).size == (267, 400)
    assert _image(db_client, second, "original").headers["content-type"] == "image/heic"

    assert db_client.get(f"/journals/{journal_id}").json()["pageCount"] == 2
    assert _files(data_dir) == [
        f"pages/{first['id']}/normalized.jpg",
        f"pages/{first['id']}/original.jpg",
        f"pages/{first['id']}/thumbnail.jpg",
        f"pages/{second['id']}/normalized.jpg",
        f"pages/{second['id']}/original.heic",
        f"pages/{second['id']}/thumbnail.jpg",
    ]


def test_uploading_the_same_photo_again_gives_back_the_page(
    db_client: TestClient, make_image: MakeImage
) -> None:
    journal_id = _journal(db_client)
    photo, other = make_image(color="red"), make_image(color="green")
    first = _upload(db_client, journal_id, ("a.jpg", photo))["items"][0]

    items = _upload(db_client, journal_id, ("again.jpg", photo), ("b.jpg", other))["items"]

    assert items[0]["duplicate"] is True
    assert items[0]["filename"] == "again.jpg"
    assert items[0]["page"] == first["page"]
    assert items[1]["duplicate"] is False
    assert items[1]["page"]["pageNumber"] == 2
    assert db_client.get(f"/journals/{journal_id}").json()["pageCount"] == 2


def test_the_same_photo_twice_in_one_upload(db_client: TestClient, make_image: MakeImage) -> None:
    journal_id = _journal(db_client)
    photo = make_image()
    items = _upload(db_client, journal_id, ("a.jpg", photo), ("b.jpg", photo))["items"]
    assert [item["duplicate"] for item in items] == [False, True]
    assert items[0]["page"]["id"] == items[1]["page"]["id"]


def test_dedupe_is_per_journal(db_client: TestClient, make_image: MakeImage) -> None:
    photo = make_image()
    _upload(db_client, _journal(db_client, "One"), ("a.jpg", photo))
    item = _upload(db_client, _journal(db_client, "Two"), ("a.jpg", photo))["items"][0]
    assert item["duplicate"] is False


def test_start_page_number(db_client: TestClient, make_image: MakeImage) -> None:
    journal_id = _journal(db_client)
    items = _upload(
        db_client,
        journal_id,
        ("a.jpg", make_image(color="red")),
        ("b.jpg", make_image(color="green")),
        startPageNumber=10,
    )["items"]
    assert [item["page"]["pageNumber"] for item in items] == [10, 11]

    # The default carries on after the highest number.
    item = _upload(db_client, journal_id, ("c.jpg", make_image(color="blue")))["items"][0]
    assert item["page"]["pageNumber"] == 12


def test_taken_page_number_is_409(
    db_client: TestClient, make_image: MakeImage, data_dir: Path
) -> None:
    journal_id = _journal(db_client)
    _upload(db_client, journal_id, ("a.jpg", make_image(color="red")), startPageNumber=5)

    response = _post(
        db_client,
        journal_id,
        ("b.jpg", make_image(color="green")),
        ("c.jpg", make_image(color="blue")),
        startPageNumber=4,
    )
    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    assert db_client.get(f"/journals/{journal_id}").json()["pageCount"] == 1
    assert len(_files(data_dir)) == 3


def test_one_bad_file_stores_nothing(
    db_client: TestClient, make_image: MakeImage, data_dir: Path
) -> None:
    journal_id = _journal(db_client)
    response = _post(db_client, journal_id, ("good.jpg", make_image()), ("notes.txt", b"just text"))
    assert response.status_code == 415
    assert response.headers["content-type"] == "application/problem+json"
    assert "notes.txt" in response.json()["detail"]
    assert db_client.get(f"/journals/{journal_id}").json()["pageCount"] == 0
    assert _files(data_dir) == []


def test_files_over_25_mb_are_413(db_client: TestClient, data_dir: Path) -> None:
    journal_id = _journal(db_client)
    response = _post(db_client, journal_id, ("huge.jpg", b"\xff" * (MAX_FILE_BYTES + 1)))
    assert response.status_code == 413
    assert "huge.jpg" in response.json()["detail"]
    assert _files(data_dir) == []


def test_upload_needs_files(db_client: TestClient) -> None:
    response = db_client.post(f"/journals/{_journal(db_client)}/pages", data={"x": "1"})
    assert response.status_code == 422


def test_upload_to_unknown_journal_is_404(db_client: TestClient, make_image: MakeImage) -> None:
    response = _post(db_client, new_id(Prefix.JOURNAL), ("a.jpg", make_image()))
    assert response.status_code == 404
    assert response.json()["detail"] == "Journal not found."


def _page_ids(client: TestClient, **params: str | int) -> list[str]:
    ids, cursor = [], None
    while True:
        body = client.get("/pages", params=params | ({"cursor": cursor} if cursor else {}))
        assert body.status_code == 200, body.text
        ids += [page["id"] for page in body.json()["items"]]
        if (cursor := body.json()["nextCursor"]) is None:
            return ids


def _pages(client: TestClient, journal_id: str, count: int, make_image: MakeImage) -> list[str]:
    files = [(f"{n}.png", make_image("PNG", color=(n, n, n))) for n in range(count)]
    return [item["page"]["id"] for item in _upload(client, journal_id, *files)["items"]]


def test_list_is_newest_journal_first_then_page_order(
    db_client: TestClient, make_image: MakeImage
) -> None:
    older, newer = _journal(db_client, "Older"), _journal(db_client, "Newer")
    older_pages = _pages(db_client, older, 3, make_image)
    newer_pages = _pages(db_client, newer, 2, make_image)
    # Page numbers decide the order, not upload order.
    db_client.patch(f"/pages/{older_pages[0]}", json={"pageNumber": 9})

    ids = _page_ids(db_client, limit=2)
    mine = [page_id for page_id in ids if page_id in older_pages + newer_pages]
    assert mine == [*newer_pages, older_pages[1], older_pages[2], older_pages[0]]
    assert len(ids) == len(set(ids))


def test_list_filters(db_client: TestClient, make_image: MakeImage) -> None:
    journal_id = _journal(db_client)
    july, august, undated = _pages(db_client, journal_id, 3, make_image)
    db_client.patch(f"/pages/{july}", json={"entryDates": ["2026-07-14", "2026-07-15"]})
    db_client.patch(f"/pages/{august}", json={"entryDates": ["2026-08-01"]})

    def listed(**params: str) -> list[str]:
        return _page_ids(db_client, journalId=journal_id, **params)

    assert listed() == [july, august, undated]
    assert listed(status="uploaded") == [july, august, undated]
    assert listed(status="ready") == []
    assert listed(dateFrom="2026-07-15") == [july, august]
    assert listed(dateTo="2026-07-31") == [july]
    assert listed(dateFrom="2026-07-16", dateTo="2026-07-31") == []
    assert listed(dateFrom="2026-08-01", dateTo="2026-08-01") == [august]


def test_cursor_of_a_deleted_page_still_works(db_client: TestClient, make_image: MakeImage) -> None:
    journal_id = _journal(db_client)
    first, second, third = _pages(db_client, journal_id, 3, make_image)
    body = db_client.get("/pages", params={"journalId": journal_id, "limit": 1}).json()
    assert [page["id"] for page in body["items"]] == [first]
    db_client.delete(f"/pages/{first}")

    rest = db_client.get("/pages", params={"journalId": journal_id, "cursor": body["nextCursor"]})
    assert [page["id"] for page in rest.json()["items"]] == [second, third]


@pytest.mark.parametrize(
    "day", ["0", "1784073600", "-3.2e-276", "2026-7-14", "2026-07-14T00:00:00"]
)
def test_dates_must_be_iso_days(db_client: TestClient, make_image: MakeImage, day: str) -> None:
    response = db_client.get("/pages", params={"dateFrom": day})
    assert response.status_code == 422
    assert [error["parameter"] for error in response.json()["errors"]] == ["dateFrom"]
    (page_id,) = _pages(db_client, _journal(db_client), 1, make_image)
    for value in (day, 0, 1784073600):
        response = db_client.patch(f"/pages/{page_id}", json={"entryDates": [value]})
        assert response.status_code == 422


@pytest.mark.parametrize(
    "cursor",
    ["nope", new_id(Prefix.PAGE), new_id(Prefix.JOURNAL), f"{new_id(Prefix.JOURNAL)}.0"],
)
def test_malformed_cursor_is_422(db_client: TestClient, cursor: str) -> None:
    response = db_client.get("/pages", params={"cursor": cursor})
    assert response.status_code == 422
    assert [error["parameter"] for error in response.json()["errors"]] == ["cursor"]


def test_get_page(db_client: TestClient, make_image: MakeImage) -> None:
    journal_id = _journal(db_client)
    page = _upload(db_client, journal_id, ("a.jpg", make_image()))["items"][0]["page"]
    detail = db_client.get(f"/pages/{page['id']}").json()
    assert detail == {**page, "blocks": []}


def test_unknown_page_is_404(db_client: TestClient) -> None:
    page_id = new_id(Prefix.PAGE)
    for method, path in [
        ("GET", f"/pages/{page_id}"),
        ("PATCH", f"/pages/{page_id}"),
        ("DELETE", f"/pages/{page_id}"),
        ("GET", f"/pages/{page_id}/image"),
    ]:
        response = db_client.request(method, path, json={} if method == "PATCH" else None)
        assert response.status_code == 404
        assert response.json()["detail"] == "Page not found."


def test_update_changes_only_the_given_fields(db_client: TestClient, make_image: MakeImage) -> None:
    journal_id = _journal(db_client)
    page = _upload(db_client, journal_id, ("a.jpg", make_image()))["items"][0]["page"]

    labelled = db_client.patch(
        f"/pages/{page['id']}",
        json={"pageLabel": "S. 12", "entryDates": ["2026-07-15", "2026-07-14", "2026-07-15"]},
    ).json()
    assert labelled["pageLabel"] == "S. 12"
    assert labelled["entryDates"] == ["2026-07-14", "2026-07-15"]
    assert labelled["pageNumber"] == 1
    assert labelled["updatedAt"] > page["updatedAt"]

    renumbered = db_client.patch(f"/pages/{page['id']}", json={"pageNumber": 7}).json()
    assert renumbered["pageNumber"] == 7
    assert renumbered["pageLabel"] == "S. 12"

    cleared = db_client.patch(
        f"/pages/{page['id']}", json={"pageLabel": None, "entryDates": []}
    ).json()
    assert (cleared["pageLabel"], cleared["entryDates"]) == (None, [])

    assert db_client.patch(f"/pages/{page['id']}", json={}).json() == cleared


@pytest.mark.parametrize("field", ["journalId", "pageNumber", "entryDates"])
def test_update_rejects_null_for_required_fields(
    db_client: TestClient, make_image: MakeImage, field: str
) -> None:
    journal_id = _journal(db_client)
    page = _upload(db_client, journal_id, ("a.jpg", make_image()))["items"][0]["page"]
    response = db_client.patch(f"/pages/{page['id']}", json={field: None})
    assert response.status_code == 422
    assert [error["pointer"] for error in response.json()["errors"]] == [f"/{field}"]


def test_update_to_a_taken_page_number_is_409(db_client: TestClient, make_image: MakeImage) -> None:
    journal_id = _journal(db_client)
    first, second = _pages(db_client, journal_id, 2, make_image)
    response = db_client.patch(f"/pages/{second}", json={"pageNumber": 1})
    assert response.status_code == 409
    assert response.json()["detail"] == "Page number 1 is taken in that journal."
    # Keeping its own number is fine.
    assert db_client.patch(f"/pages/{first}", json={"pageNumber": 1}).status_code == 200


def test_move_to_another_journal(db_client: TestClient, make_image: MakeImage) -> None:
    source, target = _journal(db_client, "Source"), _journal(db_client, "Target")
    _pages(db_client, target, 2, make_image)
    page = _upload(db_client, source, ("a.jpg", make_image(color="navy")))["items"][0]["page"]

    moved = db_client.patch(f"/pages/{page['id']}", json={"journalId": target}).json()
    assert moved["journalId"] == target
    assert moved["pageNumber"] == 3
    assert db_client.get(f"/journals/{source}").json()["pageCount"] == 0

    back = db_client.patch(f"/pages/{page['id']}", json={"journalId": source, "pageNumber": 4})
    assert back.json()["pageNumber"] == 4


def test_move_conflicts(db_client: TestClient, make_image: MakeImage) -> None:
    source, target = _journal(db_client, "Source"), _journal(db_client, "Target")
    photo = make_image()
    page = _upload(db_client, source, ("a.jpg", photo))["items"][0]["page"]
    _upload(db_client, target, ("a.jpg", photo))

    same_image = db_client.patch(f"/pages/{page['id']}", json={"journalId": target})
    assert same_image.status_code == 409
    assert same_image.json()["detail"] == "That journal already has a page with this image."

    unknown = db_client.patch(f"/pages/{page['id']}", json={"journalId": new_id(Prefix.JOURNAL)})
    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "Journal not found."


def test_delete_page_removes_its_files(
    db_client: TestClient, make_image: MakeImage, data_dir: Path
) -> None:
    journal_id = _journal(db_client)
    kept, gone = _pages(db_client, journal_id, 2, make_image)

    response = db_client.delete(f"/pages/{gone}")
    assert response.status_code == 204
    assert db_client.get(f"/pages/{gone}").status_code == 404
    assert {path.split("/")[1] for path in _files(data_dir)} == {kept}


def test_delete_journal_removes_its_page_files(
    db_client: TestClient, make_image: MakeImage, data_dir: Path
) -> None:
    kept = _pages(db_client, _journal(db_client, "Kept"), 1, make_image)
    gone = _journal(db_client, "Gone")
    _pages(db_client, gone, 2, make_image)

    assert db_client.delete(f"/journals/{gone}").status_code == 204
    assert {path.split("/")[1] for path in _files(data_dir)} == set(kept)


def test_unknown_variant_is_422(db_client: TestClient, make_image: MakeImage) -> None:
    (page_id,) = _pages(db_client, _journal(db_client), 1, make_image)
    response = db_client.get(f"/pages/{page_id}/image", params={"variant": "huge"})
    assert response.status_code == 422
    assert [error["parameter"] for error in response.json()["errors"]] == ["variant"]


def test_missing_image_file_is_404(
    db_client: TestClient, make_image: MakeImage, data_dir: Path
) -> None:
    (page_id,) = _pages(db_client, _journal(db_client), 1, make_image)
    (data_dir / "pages" / page_id / "normalized.jpg").unlink()
    response = db_client.get(f"/pages/{page_id}/image")
    assert response.status_code == 404
    assert response.json()["detail"] == "Image file not found."
