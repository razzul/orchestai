# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents.orchestrator import run_orchestrator
from db.database import AsyncSessionLocal
from db.models import Task
from sqlalchemy import select
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="OrchestAI", version="1.0.0")


class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str


@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        result = await run_orchestrator(req.user_id, req.session_id, req.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks")
async def get_tasks(user_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Task).where(Task.user_id == user_id))
        tasks = result.scalars().all()
        return [{"id": str(t.id), "title": t.title, "status": t.status, "priority": t.priority, "due_date": str(t.due_date)} for t in tasks]


@app.get("/health")
def health():
    return {"status": "ok", "service": "OrchestAI"}