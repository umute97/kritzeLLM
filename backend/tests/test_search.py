import itertools
import math
import re
import uuid
import zlib
from collections.abc import Callable, Sequence
from typing import Any

import pytest
from conftest import FakeVisionModel, new_journal, ok, run_sql, upload
from fastapi.testclient import TestClient
from pydantic_ai.embeddings import Embedder, EmbeddingResult, TestEmbeddingModel
from pydantic_ai.exceptions import ModelHTTPError
from sqlalchemy import update

from kritzellm.config import Settings
from kritzellm.core import embeddings
from kritzellm.core.embeddings import EMBED_DIMENSIONS
from kritzellm.db import models as db

pytestmark = pytest.mark.db

MakeImage = Callable[..., bytes]
_sizes = itertools.count()
"""Every page image gets its own width, so none is taken for a re-upload of another."""


class WordsModel(TestEmbeddingModel):
    """A fake embedding model that means something: one dimension per word, so texts sharing
    more words are closer. Counts its calls."""

    def __init__(self) -> None:
        super().__init__(dimensions=EMBED_DIMENSIONS)
        self.calls = 0

    async def embed(
        self, inputs: str | Sequence[str], *, input_type: Any, settings: Any = None
    ) -> EmbeddingResult:
        self.calls += 1
        result = await super().embed(inputs, input_type=input_type, settings=settings)
        result.embeddings = [_words_vector(text) for text in result.inputs]
        return result


def _words_vector(text: str) -> list[float]:
    vector = [0.0] * EMBED_DIMENSIONS
    vector[0] = 0.1  # so a text without words still has a direction
    for word in re.findall(r"\w+", text.lower()):
        vector[1 + zlib.crc32(word.encode()) % (EMBED_DIMENSIONS - 1)] += 1.0
    length = math.sqrt(sum(value * value for value in vector))
    return [value / length for value in vector]


class FailingModel(TestEmbeddingModel):
    async def embed(self, *args: Any, **kwargs: Any) -> EmbeddingResult:
        raise ModelHTTPError(503, "text-embedding-3-small", body="overloaded")


def _use_model(monkeypatch: pytest.MonkeyPatch, model: TestEmbeddingModel) -> None:
    """Embeds with `model` everywhere: in the worker and in the API's thread."""
    embedder = Embedder(model, settings={"dimensions": EMBED_DIMENSIONS})
    monkeypatch.setattr(embeddings, "_embedder", lambda name, api_key: embedder)


@pytest.fixture
def words_model(monkeypatch: pytest.MonkeyPatch) -> WordsModel:
    model = WordsModel()
    _use_model(monkeypatch, model)
    return model


def word() -> str:
    """A word no other page has, so searches don't find other tests' pages."""
    return f"wort{uuid.uuid4().hex[:10]}"


def transcription(*texts: str, dates: Sequence[str] = ()) -> dict[str, Any]:
    blocks = [{"kind": "paragraph", "text": text, "uncertain": False} for text in texts]
    return {"page_label": None, "entry_dates": list(dates), "blocks": blocks}


@pytest.fixture
def add_pages(
    db_client: TestClient,
    make_image: MakeImage,
    vision_model: FakeVisionModel,
    work: Callable[[], None],
    words_model: WordsModel,
) -> Callable[..., list[dict]]:
    """Uploads pages that read as the given transcriptions and indexes them. Returns the pages."""

    def add(journal_id: str, *transcriptions: dict[str, Any]) -> list[dict]:
        vision_model.outputs = list(transcriptions)
        images = [make_image(size=(100 + next(_sizes), 80)) for _ in transcriptions]
        items = upload(db_client, journal_id, *images)
        assert not any(item["duplicate"] for item in items)
        work()
        return [ok(db_client.get(f"/pages/{item['page']['id']}")) for item in items]

    return add


def search(client: TestClient, q: str, **params: str | int) -> list[dict]:
    return ok(client.get("/search", params={"q": q, **params}))["items"]


def page_ids(hits: list[dict]) -> list[str]:
    return [hit["page"]["id"] for hit in hits]


@pytest.fixture
def journal(db_client: TestClient) -> str:
    return new_journal(db_client)


def test_keyword_search_finds_a_word(
    db_client: TestClient, journal: str, add_pages: Callable[..., list[dict]]
) -> None:
    rare = word()
    found, _ = add_pages(
        journal,
        transcription("Heute Kuchen gebacken.", f"Mit {rare} und Zucker."),
        transcription("Nur Regen heute."),
    )

    (hit,) = search(db_client, rare.upper(), mode="keyword", journalId=journal)

    assert hit["page"]["id"] == found["id"]
    assert hit["page"]["status"] == "ready"
    assert [block["id"] for block in hit["blocks"]] == [block["id"] for block in found["blocks"]]
    assert (hit["keywordRank"], hit["vectorRank"]) == (1, None)
    assert hit["score"] > 0


def test_keyword_search_takes_quoted_phrases(
    db_client: TestClient, journal: str, add_pages: Callable[..., list[dict]]
) -> None:
    first, second = word(), word()
    in_order, _ = add_pages(
        journal,
        transcription(f"{first} {second} am Abend."),
        transcription(f"{second} kam vor {first}."),
    )

    assert page_ids(
        search(db_client, f'"{first} {second}"', mode="keyword", journalId=journal)
    ) == [in_order["id"]]
    assert len(search(db_client, f"{first} {second}", mode="keyword", journalId=journal)) == 2


def test_vector_search_ranks_by_meaning(
    db_client: TestClient,
    journal: str,
    add_pages: Callable[..., list[dict]],
    words_model: WordsModel,
) -> None:
    one, two, three = word(), word(), word()
    some, most, none = add_pages(
        journal,
        transcription(f"{one} war da."),
        transcription(f"{one} {two} {three} war da."),
        transcription("Ganz was anderes."),
    )
    calls = words_model.calls

    hits = search(db_client, f"{one} {two} {three}", mode="vector", journalId=journal)

    assert page_ids(hits) == [most["id"], some["id"], none["id"]]
    assert [hit["vectorRank"] for hit in hits] == [1, 2, 3]
    assert all(hit["keywordRank"] is None for hit in hits)
    assert hits[0]["score"] > hits[1]["score"] > hits[2]["score"]
    assert words_model.calls == calls + 1


def test_vector_search_skips_chunks_of_another_model(
    db_client: TestClient,
    settings: Settings,
    journal: str,
    add_pages: Callable[..., list[dict]],
) -> None:
    rare = word()
    (page,) = add_pages(journal, transcription(f"{rare} im Garten."))
    run_sql(
        str(settings.database_url),
        update(db.Chunk).where(db.Chunk.page_id == page["id"]).values(embed_model="old-model"),
    )

    assert search(db_client, rare, mode="vector", journalId=journal) == []
    assert page_ids(search(db_client, rare, mode="keyword", journalId=journal)) == [page["id"]]


def test_hybrid_search_fuses_both_rankings(
    db_client: TestClient, journal: str, add_pages: Callable[..., list[dict]]
) -> None:
    rare, other = word(), word()
    both, vector_only = add_pages(
        journal,
        transcription(f"{rare} {other} heute."),
        transcription(f"{other} {other} {other} gestern."),
    )

    hits = search(db_client, rare, journalId=journal)

    assert page_ids(hits) == [both["id"], vector_only["id"]]
    assert (hits[0]["vectorRank"], hits[0]["keywordRank"]) == (1, 1)
    assert (hits[1]["vectorRank"], hits[1]["keywordRank"]) == (2, None)
    assert hits[0]["score"] == pytest.approx(2 / 61)
    assert hits[1]["score"] == pytest.approx(1 / 62)


def test_a_page_is_one_hit_with_its_best_chunk(
    db_client: TestClient, journal: str, add_pages: Callable[..., list[dict]]
) -> None:
    rare = word()
    (page,) = add_pages(
        journal, transcription("Füllwort " * 300, f"{rare} " + "Ende " * 299, "Schluss " * 200)
    )
    assert len(page["blocks"]) == 3

    for mode in ("hybrid", "vector", "keyword"):
        (hit,) = search(db_client, rare, mode=mode, journalId=journal)
        assert [block["id"] for block in hit["blocks"]] == [page["blocks"][1]["id"]], mode


@pytest.mark.parametrize("mode", ["hybrid", "vector", "keyword", "exact"])
def test_filters_by_journal_and_date(
    db_client: TestClient, add_pages: Callable[..., list[dict]], mode: str
) -> None:
    rare = word()
    journal, other_journal = new_journal(db_client), new_journal(db_client)
    january, march, undated = add_pages(
        journal,
        transcription(f"{rare} im Januar.", dates=["2026-01-05"]),
        transcription(f"{rare} im März.", dates=["2026-02-27", "2026-03-02"]),
        transcription(f"{rare} irgendwann."),
    )
    (elsewhere,) = add_pages(other_journal, transcription(f"{rare} woanders."))

    def found(**params: str) -> set[str]:
        return set(page_ids(search(db_client, rare, mode=mode, **params)))

    assert found(journalId=journal) == {january["id"], march["id"], undated["id"]}
    assert found(journalId=other_journal) == {elsewhere["id"]}
    assert found(journalId=journal, dateFrom="2026-03-01") == {march["id"]}
    assert found(journalId=journal, dateTo="2026-02-27") == {january["id"], march["id"]}
    assert found(dateFrom="2026-01-01", dateTo="2026-01-31") >= {january["id"]}
    assert not found(dateFrom="2026-01-01", dateTo="2026-01-31") & {march["id"], undated["id"]}


def test_exact_search_finds_text_as_written(
    db_client: TestClient, journal: str, add_pages: Callable[..., list[dict]]
) -> None:
    name = word()
    first, second, _ = add_pages(
        journal,
        transcription(f"Besuch bei Oma {name}.", "Nichts weiter.", f"Tschüss, OMA {name.upper()}!"),
        transcription(f"Oma {name}s Geburtstag"),
        transcription(f"Oma und {name}"),
    )

    hits = search(db_client, f"oma {name[:-2]}", mode="exact", journalId=journal)

    assert page_ids(hits) == [first["id"], second["id"]]
    assert [block["id"] for block in hits[0]["blocks"]] == [
        first["blocks"][0]["id"],
        first["blocks"][2]["id"],
    ]
    assert [hit["score"] for hit in hits] == [2, 1]
    assert all(hit["vectorRank"] is None and hit["keywordRank"] is None for hit in hits)


def test_exact_search_takes_wildcards_literally(
    db_client: TestClient, journal: str, add_pages: Callable[..., list[dict]]
) -> None:
    rare = word()
    percent, _ = add_pages(
        journal, transcription(f"{rare} zu 50% sicher."), transcription(f"{rare} 500 Mal_")
    )

    assert page_ids(search(db_client, "50%", mode="exact", journalId=journal)) == [percent["id"]]
    assert search(db_client, "%", mode="exact", journalId=journal) == search(
        db_client, "50%", mode="exact", journalId=journal
    )
    assert len(search(db_client, "_", mode="exact", journalId=journal)) == 1


def test_limit_and_no_hits(
    db_client: TestClient, journal: str, add_pages: Callable[..., list[dict]]
) -> None:
    rare = word()
    add_pages(journal, *(transcription(f"{rare} Nummer {n}.") for n in range(3)))

    for mode in ("hybrid", "vector", "keyword", "exact"):
        assert len(search(db_client, rare, mode=mode, journalId=journal, limit=2)) == 2, mode
    assert search(db_client, word(), mode="keyword", journalId=journal) == []
    assert search(db_client, word(), mode="exact", journalId=journal) == []


@pytest.mark.parametrize(
    ("params", "parameter"),
    [
        ({}, "q"),
        ({"q": "   "}, "q"),
        ({"q": "x" * 501}, "q"),
        ({"q": "Oma", "mode": "fuzzy"}, "mode"),
        ({"q": "Oma", "limit": 51}, "limit"),
    ],
)
def test_bad_parameters_are_422(
    db_client: TestClient, params: dict[str, str | int], parameter: str
) -> None:
    response = db_client.get("/search", params=params)

    assert response.status_code == 422
    assert [error["parameter"] for error in response.json()["errors"]] == [parameter]


def test_an_unreachable_embedding_model_is_502_but_keywords_still_work(
    db_client: TestClient,
    journal: str,
    add_pages: Callable[..., list[dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rare = word()
    (page,) = add_pages(journal, transcription(f"{rare} im Regen."))
    _use_model(monkeypatch, FailingModel())

    for mode in ("hybrid", "vector"):
        response = db_client.get("/search", params={"q": rare, "mode": mode})
        assert response.status_code == 502
        assert response.headers["content-type"] == "application/problem+json"
        assert "overloaded" not in response.text
    for mode in ("keyword", "exact"):
        assert page_ids(search(db_client, rare, mode=mode, journalId=journal)) == [page["id"]]
