"""Reading a page image into ordered text blocks with a vision model.

One structured-output call per page: the model gets the normalized JPEG and answers with a
`PageTranscription`. Output that doesn't validate goes back to the model once, then the run fails.
The model name `test` swaps in PydanticAI's fake model, so the stack runs without an OpenAI key.
"""

import logging
from datetime import date

from pydantic import BaseModel, Field
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from kritzellm.api.schemas.blocks import BlockKind
from kritzellm.config import Settings

logger = logging.getLogger(__name__)

TEST_MODEL = "test"
"""Model name for PydanticAI's fake model: made-up but valid output, no API calls."""

INSTRUCTIONS = """\
You transcribe one photographed page of a handwritten journal.

- Transcribe faithfully, in the page's own language. Don't correct spelling, grammar or wording,
  and don't translate or summarize.
- Split the page into blocks: one per visual paragraph, heading, list or note in the margin,
  in the order a person would read them.
- Keep line breaks inside lists, one item per line.
- Write each word you can't read as [?] and mark that block as uncertain. Also mark a block as
  uncertain when you had to guess at parts of it.
- Describe drawings, doodles and stuck-in things briefly in square brackets, in the page's language,
  as a block of kind drawing.
- page_label is a page number or label written on the page itself, otherwise null.
- entry_dates are the dates of the entries on the page, only as written there. Leave the list empty
  when the page shows no date; never guess one.
- A blank page has no blocks.
"""


class TranscribedBlock(BaseModel):
    """One piece of text on the page."""

    kind: BlockKind
    text: str = Field(min_length=1)
    """The text as written, with [?] for unreadable words."""
    uncertain: bool
    """Whether parts of the text are unreadable or guessed."""


class PageTranscription(BaseModel):
    """Everything read from one page."""

    page_label: str | None = Field(max_length=40)
    """Page number or label written on the page, if any."""
    entry_dates: list[date]
    """Dates of the entries on the page, as written there."""
    blocks: list[TranscribedBlock]
    """The page's blocks in reading order."""


agent = Agent(output_type=PageTranscription, instructions=INSTRUCTIONS, retries={"output": 1})


def _model(name: str, settings: Settings) -> Model | str:
    if name == TEST_MODEL:
        return TEST_MODEL
    api_key = settings.openai_api_key
    provider = OpenAIProvider(api_key=api_key.get_secret_value() if api_key else None)
    return OpenAIResponsesModel(
        name,
        provider=provider,
        settings=OpenAIResponsesModelSettings(openai_reasoning_effort="high"),
    )


async def transcribe(
    image: bytes, settings: Settings, *, model: str | None = None
) -> PageTranscription:
    """Reads a normalized page image (JPEG), with `model` instead of the configured one if given."""
    name = model or settings.transcribe_model
    page = BinaryContent(image, media_type="image/jpeg", vendor_metadata={"detail": "high"})
    result = await agent.run(["Transcribe this page.", page], model=_model(name, settings))
    usage = result.usage
    logger.info(
        "Transcribed a page with %s: %d input + %d output tokens in %d request(s)",
        name,
        usage.input_tokens,
        usage.output_tokens,
        usage.requests,
    )
    return result.output
