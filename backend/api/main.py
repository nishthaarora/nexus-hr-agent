from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from rag.agent import UserAgentTool
from rag.sse import sse_event
from pydantic import BaseModel, Field, field_validator
from fastapi.middleware.cors import CORSMiddleware
from backend.session_store import save_history, load_or_create_session
from rag.summarize import summarize_if_needed
from backend.auth import require_api_key
from rag.exceptions import (
    MaxTokensReachedError,
    TooManyToolCallsError,
    RateLimitedError,
    ContextTooLargeError,
    AgentError,
)
from rag.rate_limit import enforce_session_rate_limit, enforce_api_key_rate_limit
from dotenv import load_dotenv
load_dotenv()

import uuid
import os

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=3000)
    session_id: str | None = None
    
@classmethod
@field_validator("question")
def question_must_be_clean(cls, v: str) -> str:
    if not v.strip:
        raise ValueError("question cannot be empty or whitesoace")
    if "\x00" in v:
        raise ValueError("question cannot contain invalid characters")
    return v

@classmethod
@field_validator("session_id")
def session_id_must_be_uuid(cls, v: str | None) -> str | None:
    if v is None:
        return v
    import uuid
    try:
        uuid.UUIS(v)
    except ValueError:
        raise ValueError("session_id must be a valid UUID")
    return v


@app.get("/health")
def read_root():
    return {"status": "ok"}

@app.post("/chat")
def chat(request: ChatRequest, _None = Depends(require_api_key), _: None = Depends(enforce_api_key_rate_limit)):
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        enforce_session_rate_limit(session_id)
        session = load_or_create_session(session_id, request.question)
        session["history"] = summarize_if_needed(session["history"])
        
    except RateLimitedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ContextTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except AgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

        
    agent = UserAgentTool()
        
    def event_stream():
        yield sse_event("session_id", {"session_id": session_id})
        for chunk in agent.stream(session):
            yield chunk
        save_history(session_id, session)
        
    response = StreamingResponse(event_stream(), media_type="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    return response



@app.get("/history")
def getHistory(session_id: str, _None = Depends(require_api_key)):
    session = load_or_create_session(session_id)
    return {"history": session["history"]}


