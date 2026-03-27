"""Simulation Dialogue API routes.

Provides endpoints for:
- Starting conversations with agents
- Sending messages and getting responses
- Getting conversation history
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import GraphStoreDep
from app.config import get_settings
from app.services.interactive_dialogue import DialogueManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulation/dialogue", tags=["Interactive Dialogue"])


@router.post(
    "/start",
    summary="Start conversation",
    description="Start a new conversation with a simulation agent.",
)
async def start_conversation(
    agent_id: UUID,
    user_id: str = Query(default="anonymous", description="User identifier"),
    store: GraphStoreDep = None,
) -> dict:
    """Start a conversation with an agent."""
    try:
        settings = get_settings()

        dialogue_manager = DialogueManager(
            openai_settings=settings.openai,
            graph_store=store,
        )

        session = await dialogue_manager.start_conversation(
            user_id=user_id,
            agent_id=agent_id,
        )

        return {
            "conversation_id": session.id,
            "agent_id": str(agent_id),
            "user_id": user_id,
            "started_at": session.started_at.isoformat(),
            "status": "active",
            "message": "Conversation started successfully",
        }

    except Exception as e:
        logger.exception("Failed to start conversation: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start conversation: {e}",
        ) from e


@router.post(
    "/message",
    summary="Send message",
    description="Send a message to an agent and get a response.",
)
async def send_message(
    conversation_id: str,
    message: str,
    store: GraphStoreDep = None,
) -> dict:
    """Send a message and get agent response."""
    try:
        settings = get_settings()

        dialogue_manager = DialogueManager(
            openai_settings=settings.openai,
            graph_store=store,
        )

        response = await dialogue_manager.process_user_message(
            conversation_id=conversation_id,
            message=message,
        )

        return {
            "conversation_id": conversation_id,
            "user_message": message,
            "agent_response": response.message,
            "emotion": response.emotion,
            "suggested_actions": response.suggested_actions,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Failed to send message: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {e}",
        ) from e


@router.get(
    "/{conversation_id}/history",
    summary="Get conversation history",
    description="Get the full conversation history.",
)
async def get_conversation_history(
    conversation_id: str,
    store: GraphStoreDep = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """Get conversation history."""
    try:
        settings = get_settings()

        dialogue_manager = DialogueManager(
            openai_settings=settings.openai,
            graph_store=store,
        )

        messages = await dialogue_manager.get_conversation_history(conversation_id)

        # Apply limit
        messages = messages[-limit:]

        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "id": m.id,
                    "sender": m.sender,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": m.metadata,
                }
                for m in messages
            ],
            "total": len(messages),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Failed to get conversation history: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation history: {e}",
        ) from e


@router.get(
    "/user/{user_id}/sessions",
    summary="Get user sessions",
    description="Get all conversation sessions for a user.",
)
async def get_user_sessions(
    user_id: str,
    store: GraphStoreDep = None,
) -> dict:
    """Get user's conversation sessions."""
    try:
        settings = get_settings()

        dialogue_manager = DialogueManager(
            openai_settings=settings.openai,
            graph_store=store,
        )

        sessions = dialogue_manager.list_user_sessions(user_id)

        return {
            "user_id": user_id,
            "sessions": [
                {
                    "id": s.id,
                    "agent_id": str(s.agent_id),
                    "started_at": s.started_at.isoformat(),
                    "last_activity": s.last_activity.isoformat(),
                    "message_count": len(s.messages),
                }
                for s in sessions
            ],
            "total": len(sessions),
        }

    except Exception as e:
        logger.exception("Failed to get user sessions: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user sessions: {e}",
        ) from e


@router.post(
    "/agents/{agent_id}/chat",
    summary="Direct chat with agent",
    description="Start a new conversation and send a message in one request.",
)
async def direct_chat(
    agent_id: UUID,
    message: str,
    user_id: str = Query(default="anonymous", description="User identifier"),
    store: GraphStoreDep = None,
) -> dict:
    """Direct chat with an agent (start + message in one request)."""
    try:
        settings = get_settings()

        dialogue_manager = DialogueManager(
            openai_settings=settings.openai,
            graph_store=store,
        )

        # Start conversation
        session = await dialogue_manager.start_conversation(
            user_id=user_id,
            agent_id=agent_id,
        )

        # Send message
        response = await dialogue_manager.process_user_message(
            conversation_id=session.id,
            message=message,
        )

        return {
            "conversation_id": session.id,
            "agent_id": str(agent_id),
            "user_message": message,
            "agent_response": response.message,
            "emotion": response.emotion,
            "suggested_actions": response.suggested_actions,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.exception("Failed to chat with agent: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to chat with agent: {e}",
        ) from e
