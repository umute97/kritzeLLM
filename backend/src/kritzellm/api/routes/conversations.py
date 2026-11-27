from fastapi import APIRouter, Request, Response, status

from kritzellm.core import conversations as core

from ..deps import Session
from ..errors import problem_responses
from ..schemas.conversations import (
    Conversation,
    ConversationCreate,
    ConversationDetail,
    ConversationList,
    ConversationUpdate,
)
from .params import ConversationCursor, ConversationIdPath, Limit, location_header

router = APIRouter(tags=["conversations"], responses=problem_responses(400, 401, 422))


@router.get(
    "/conversations",
    summary="List conversations",
)
async def list_conversations(
    session: Session, limit: Limit = 25, cursor: ConversationCursor = None
) -> ConversationList:
    """Lists all conversations, the most recently active first."""
    conversations, next_cursor = await core.list_conversations(session, limit=limit, cursor=cursor)
    return ConversationList(
        items=[Conversation.model_validate(conversation) for conversation in conversations],
        next_cursor=next_cursor,
    )


@router.post(
    "/conversations",
    status_code=status.HTTP_201_CREATED,
    summary="Start a conversation",
    responses={
        201: {"headers": location_header("URL of the new conversation.")},
    },
)
async def create_conversation(
    body: ConversationCreate, session: Session, request: Request, response: Response
) -> Conversation:
    """Starts an empty conversation to ask the journal things in."""
    conversation = await core.create_conversation(session, title=body.title)
    await session.commit()
    response.headers["Location"] = request.url_for(
        "get_conversation", conversationId=conversation.id
    ).path
    return Conversation.model_validate(conversation)


@router.get(
    "/conversations/{conversationId}",
    summary="Get a conversation",
    responses=problem_responses(404),
)
async def get_conversation(
    conversation_id: ConversationIdPath, session: Session
) -> ConversationDetail:
    """Returns a conversation with all of its messages, oldest first.

    A conversation takes up to 20 questions, so it holds at most 40 messages.
    """
    return ConversationDetail.model_validate(await core.get_conversation(session, conversation_id))


@router.patch(
    "/conversations/{conversationId}",
    summary="Update a conversation",
    responses=problem_responses(404),
)
async def update_conversation(
    conversation_id: ConversationIdPath, body: ConversationUpdate, session: Session
) -> Conversation:
    """Renames a conversation. Only the given fields change."""
    changes = body.model_dump(exclude_unset=True, by_alias=False)
    conversation = await core.update_conversation(session, conversation_id, changes)
    await session.commit()
    return Conversation.model_validate(conversation)


@router.delete(
    "/conversations/{conversationId}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a conversation",
    responses=problem_responses(404),
)
async def delete_conversation(conversation_id: ConversationIdPath, session: Session) -> None:
    """Deletes a conversation with all of its messages.

    This can't be undone.
    """
    await core.delete_conversation(session, conversation_id)
    await session.commit()
