"""The journal's helper: a chat agent that looks things up in the journal and cites what it read.

An answer is one agent run, streamed as events. The question and the answer are saved together
once it's done, so a failed or stopped answer leaves nothing behind. The model name `test` swaps
in PydanticAI's fake model, so the stack runs without an OpenAI key.
"""

import logging
from collections.abc import AsyncGenerator, Sequence
from datetime import date
from functools import cache

from pydantic_ai import Agent, AgentRunResultEvent, RunContext, UsageLimits
from pydantic_ai.exceptions import (
    ModelAPIError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
    UserError,
)
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kritzellm.api.schemas.conversations import (
    Message,
    MessageEndEvent,
    MessageRole,
    MessageStartEvent,
    SourceEvent,
    StreamEvent,
    TextDeltaEvent,
    ToolCall,
    ToolCallEvent,
    ToolResultEvent,
)
from kritzellm.config import Settings
from kritzellm.db import models as db

from ..conversations import add_message, get_conversation
from ..errors import UpstreamError
from .citations import strip_citations
from .tools import TOOLS, Deps

logger = logging.getLogger(__name__)

TEST_MODEL = "test"
"""Model name for PydanticAI's fake model: made-up answers, no API calls."""

MAX_REQUESTS = 8
"""Model requests one answer may take, tool rounds included."""

TITLE_LENGTH = 60

INSTRUCTIONS = """\
You help someone find things in their own journal: photographed handwritten pages, transcribed
into text. You only know what the tools show you.

- Look things up before you answer. search_journal finds pages by meaning and by words,
  find_exact finds a name or phrase exactly as written, list_pages browses a journal or a stretch
  of time, read_page reads a whole page, and read_block reads around a block you've seen.
- Answer only from what the tools showed you. When the journal doesn't say, say so kindly. Never
  fill gaps from general knowledge, and never guess dates.
- Every block the tools show has a number in square brackets, like [3]. Cite the blocks your
  answer rests on right after what they support, one number per bracket: "You planted them by
  the fence [3][5]." Only cite numbers the tools showed you while answering this question.
- Answer in the language of the question, briefly and warmly, like a friend who read along. Quote
  the journal where its own words say it best.
- Entry dates are the days entries were written. Unreadable words are written as [?].
"""

agent = Agent(deps_type=Deps, instructions=INSTRUCTIONS, tools=TOOLS)


@agent.instructions
def _today_and_journals(ctx: RunContext[Deps]) -> str:
    journals = "\n".join(f"- {name} (id {id_})" for id_, name in ctx.deps.journals.items())
    return f"Today is {date.today().isoformat()}.\n\nThe journals:\n{journals or '- none yet'}"


@cache
def _openai_model(name: str, api_key: str | None) -> Model:
    """One model (and HTTP client) per name and key, shared by all answers."""
    return OpenAIResponsesModel(
        name,
        provider=OpenAIProvider(api_key=api_key),
        settings=OpenAIResponsesModelSettings(openai_reasoning_effort="low"),
    )


def _model(settings: Settings) -> Model | str:
    name = settings.chat_model
    if name == TEST_MODEL:
        return TEST_MODEL
    api_key = settings.openai_api_key
    try:
        return _openai_model(name, api_key.get_secret_value() if api_key else None)
    except UserError as exc:
        logger.error("The chat model isn't set up: %s", exc)
        raise UpstreamError("The chat model isn't set up on the server.") from exc


def _history(messages: Sequence[db.Message]) -> list[ModelMessage]:
    """Earlier questions and answers, as plain text."""
    return [
        ModelRequest(parts=[UserPromptPart(message.content)])
        if message.role == MessageRole.USER
        else ModelResponse(parts=[TextPart(strip_citations(message.content))])
        for message in messages
    ]


def title_from(question: str) -> str:
    """A conversation title from its first question: the question, cut at a word if it's long."""
    text = " ".join(question.split())
    if len(text) <= TITLE_LENGTH:
        return text
    head = text[: TITLE_LENGTH + 1]
    cut = head.rsplit(" ", 1)[0] if " " in head else text[:TITLE_LENGTH]
    return f"{cut.rstrip(' ,.;:!?')}…"


async def _journals(session: AsyncSession) -> dict[str, str]:
    rows = await session.execute(select(db.Journal.id, db.Journal.name).order_by(db.Journal.id))
    return {journal_id: name for journal_id, name in rows.all()}


async def answer(
    sessions: async_sessionmaker[AsyncSession],
    settings: Settings,
    conversation_id: str,
    question: str,
) -> AsyncGenerator[StreamEvent]:
    """Answers a question in a conversation, as the events of the stream.

    Raises `UpstreamError` when the model fails, `NotFoundError` or `ChatFullError` when the
    conversation is gone or full by the time the answer is saved.
    """
    async with sessions() as session:
        conversation = await get_conversation(session, conversation_id)
        deps = Deps(session=session, settings=settings, journals=await _journals(session))
        model = _model(settings)
        yield MessageStartEvent()

        tool_calls: dict[str, ToolCall] = {}
        output = ""
        try:
            async with agent.run_stream_events(
                question,
                message_history=_history(conversation.messages),
                model=model,
                deps=deps,
                usage_limits=UsageLimits(request_limit=MAX_REQUESTS),
            ) as events:
                async for event in events:
                    match event:
                        case (
                            PartStartEvent(part=TextPart(content=text))
                            | PartDeltaEvent(delta=TextPartDelta(content_delta=text))
                        ) if text:
                            yield TextDeltaEvent(text=text)
                        case FunctionToolCallEvent(part=call):
                            args = call.args_as_dict()
                            tool_calls[call.tool_call_id] = ToolCall(
                                name=call.tool_name, args=args, pages=0
                            )
                            yield ToolCallEvent(
                                id=call.tool_call_id, name=call.tool_name, args=args
                            )
                        case FunctionToolResultEvent(part=returned):
                            pages = deps.pages_found.get(returned.tool_call_id, 0)
                            if called := tool_calls.get(returned.tool_call_id):
                                called.pages = pages
                            name = returned.tool_name or ""
                            yield ToolResultEvent(id=returned.tool_call_id, name=name, pages=pages)
                        case AgentRunResultEvent(result=run):
                            output = run.output
                            usage = run.usage
                            logger.info(
                                "Answered a question with %s: %d input + %d output tokens in "
                                "%d request(s) and %d tool call(s)",
                                settings.chat_model,
                                usage.input_tokens,
                                usage.output_tokens,
                                usage.requests,
                                usage.tool_calls,
                            )
                        case _:
                            pass
        except UsageLimitExceeded as exc:
            logger.warning("An answer took too many steps: %s", exc)
            raise UpstreamError(
                "The helper needed too many steps for this one. Try asking more specifically."
            ) from exc
        except (ModelAPIError, UnexpectedModelBehavior) as exc:
            logger.warning("Answering a question failed: %s", exc)
            raise UpstreamError("The chat model couldn't answer. Try again later.") from exc

        content, sources = deps.citations.finish(output)
        if not content.strip():
            raise UpstreamError("The chat model came back without an answer. Try asking again.")
        await add_message(session, conversation_id, MessageRole.USER, question)
        reply = await add_message(
            session,
            conversation_id,
            MessageRole.ASSISTANT,
            content,
            tool_calls=list(tool_calls.values()),
            sources=sources,
        )
        if conversation.title is None:
            conversation.title = title_from(question)
        await session.commit()

        for source in sources:
            yield SourceEvent(source=source)
        yield MessageEndEvent(message=Message.model_validate(reply))
