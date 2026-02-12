"""Query endpoint with streaming response support.

POST /query — Accepts a natural language question, performs hybrid retrieval,
and generates an answer via LLM with streaming.
"""

import json
import logging
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI

from app.api.dependencies import GraphRetrieverDep, SettingsDep
from app.domain.schemas import QueryRequest, QueryResponse
from app.exceptions import GraphRAGError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])

_GENERATION_SYSTEM_PROMPT = """You are a knowledgeable assistant that answers questions
based on the provided context from a knowledge graph. Use the context to give accurate,
well-structured answers. If the context doesn't contain enough information, say so honestly.

Always cite which chunks or entities informed your answer when possible."""


@router.post(
    "",
    response_model=None,
    summary="Query the knowledge graph",
    description="Hybrid retrieval (vector + graph) followed by LLM generation.",
)
async def query_graph(
    request: QueryRequest,
    settings: SettingsDep,
    retriever: GraphRetrieverDep,
) -> StreamingResponse | QueryResponse:
    """Execute hybrid retrieval and return a generated answer.

    Returns a streaming response by default. The stream format is
    Server-Sent Events (SSE) with JSON payloads.
    """
    start = time.monotonic()

    try:
        # Stage 1 & 2: Hybrid retrieval
        context = await retriever.retrieve(
            query=request.question,
            top_k=request.top_k,
            traversal_depth=request.traversal_depth,
        )

        if not context.chunks:
            elapsed = (time.monotonic() - start) * 1000
            return QueryResponse(
                answer="I couldn't find any relevant information in the knowledge graph "
                "to answer your question.",
                context=context if request.include_sources else None,
                model=settings.openai.model,
                latency_ms=elapsed,
            )

        # Stage 3: LLM generation with streaming
        formatted_context = context.formatted_context
        user_prompt = (
            f"Context from knowledge graph:\n{formatted_context}\n\n"
            f"Question: {request.question}\n\n"
            f"Answer based on the above context:"
        )

        llm = ChatOpenAI(
            api_key=settings.openai.api_key,  # type: ignore[arg-type]
            base_url=settings.openai.base_url,
            model=settings.openai.model,
            temperature=0.1,
            streaming=True,
        )

        async def stream_response() -> AsyncGenerator[str, None]:
            """Generator that streams SSE events."""
            # Send context first
            if request.include_sources:
                context_event = {
                    "type": "context",
                    "data": context.model_dump(mode="json"),
                }
                yield f"data: {json.dumps(context_event)}\n\n"

            # Stream LLM tokens
            collected_answer = []
            async for token_chunk in llm.astream(
                [
                    {"role": "system", "content": _GENERATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ]
            ):
                token_text = token_chunk.content
                if isinstance(token_text, str) and token_text:
                    collected_answer.append(token_text)
                    token_event = {"type": "token", "data": token_text}
                    yield f"data: {json.dumps(token_event)}\n\n"

            # Send completion event
            elapsed = (time.monotonic() - start) * 1000
            done_event = {
                "type": "done",
                "data": {
                    "model": settings.openai.model,
                    "latency_ms": round(elapsed, 1),
                },
            }
            yield f"data: {json.dumps(done_event)}\n\n"

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except GraphRAGError as exc:
        logger.error("Query failed: %s", exc.message, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query pipeline error: {exc.message}",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected query error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during query.",
        ) from exc
