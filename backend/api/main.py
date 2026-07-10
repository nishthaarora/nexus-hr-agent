from fastapi import FastAPI
from rag.agent import run_agent
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from backend.session_store import save_history, load_or_create_session
from rag.summarize import summarize_if_needed
import uuid

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None

@app.get("/health")
def read_root():
    return {"status": "ok"}

@app.post("/chat")
def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    
    session = load_or_create_session(session_id, request.question)
    summarized_history = summarize_if_needed(session["history"])
    session["history"] = summarized_history
    
    answer, tools_used = run_agent(session)
    session["history"].append(answer)
    save_history(session_id, session)

    return {
        "answer": answer["content"][0]["text"],
        "session_id": session_id,
        "tools_used": tools_used,
    }

@app.get("/history")
def getHistory(session_id: str):
    session = load_or_create_session(session_id)
    return {"history": session["history"]}


