import asyncio
from datetime import date
from typing import Any

import pytest
from conftest import FakeVisionModel
from pydantic_ai.exceptions import UnexpectedModelBehavior, UserError
from pydantic_ai.messages import BinaryContent, UserPromptPart
from pydantic_ai.models.openai import OpenAIResponsesModel

from kritzellm.api.schemas.blocks import BlockKind
from kritzellm.config import Settings
from kritzellm.core import transcribe as transcribe_module
from kritzellm.core.transcribe import (
    INSTRUCTIONS,
    PageTranscription,
    TranscribedBlock,
    transcribe,
)

IMAGE = b"\xff\xd8 not really a JPEG"

PAGE = {
    "page_label": "12",
    "entry_dates": ["2026-03-14"],
    "blocks": [
        {"kind": "heading", "text": "14. März", "uncertain": False},
        {"kind": "paragraph", "text": "Kaffee mit [?].", "uncertain": True},
    ],
}


def _settings(**overrides: Any) -> Settings:
    return Settings(**{"transcribe_model": "gpt-test", "openai_api_key": "sk-test", **overrides})


def _read(settings: Settings | None = None) -> PageTranscription:
    return asyncio.run(transcribe(IMAGE, settings or _settings()))


def test_the_page_is_read_into_blocks(vision_model: FakeVisionModel) -> None:
    vision_model.outputs = [PAGE]

    assert _read() == PageTranscription(
        page_label="12",
        entry_dates=[date(2026, 3, 14)],
        blocks=[
            TranscribedBlock(kind=BlockKind.HEADING, text="14. März", uncertain=False),
            TranscribedBlock(kind=BlockKind.PARAGRAPH, text="Kaffee mit [?].", uncertain=True),
        ],
    )


def test_the_model_gets_the_image_and_instructions(vision_model: FakeVisionModel) -> None:
    _read()

    ((messages, info),) = vision_model.calls
    assert info.instructions == INSTRUCTIONS.strip()
    (prompt,) = [part for part in messages[0].parts if isinstance(part, UserPromptPart)]
    images = [item for item in prompt.content if isinstance(item, BinaryContent)]
    assert [(image.data, image.media_type) for image in images] == [(IMAGE, "image/jpeg")]
    assert images[0].vendor_metadata == {"detail": "high"}


def test_invalid_output_is_retried_once(vision_model: FakeVisionModel) -> None:
    vision_model.outputs = [{**PAGE, "entry_dates": ["last tuesday"]}, PAGE]

    assert _read().page_label == "12"
    assert len(vision_model.calls) == 2


def test_invalid_output_twice_fails(vision_model: FakeVisionModel) -> None:
    vision_model.outputs = [{**PAGE, "blocks": [{"kind": "poem", "text": "?", "uncertain": False}]}]

    with pytest.raises(UnexpectedModelBehavior):
        _read()
    assert len(vision_model.calls) == 2


def test_test_model_needs_no_key() -> None:
    page = _read(_settings(transcribe_model="test", openai_api_key=None))

    assert isinstance(page, PageTranscription)


def test_model_choice() -> None:
    assert transcribe_module._model("test", _settings()) == "test"
    model = transcribe_module._model("gpt-test", _settings())
    assert isinstance(model, OpenAIResponsesModel)
    assert model.model_name == "gpt-test"
    assert model.settings == {"openai_reasoning_effort": "high"}


def test_openai_without_a_key_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    with pytest.raises(UserError, match="OPENAI_API_KEY"):
        _read(_settings(openai_api_key=None))
