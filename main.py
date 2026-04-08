# main.py
import os
from dotenv import load_dotenv
load_dotenv()

# Validate required env vars on startup
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ALLOYDB_URL = os.getenv("ALLOYDB_URL")

if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY environment variable is not set")
if not ALLOYDB_URL:
    raise RuntimeError("ALLOYDB_URL environment variable is not set")

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents.orchestrator import run_orchestrator
from db.database import AsyncSessionLocal
from db.models import Task
from sqlalchemy import select
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="OrchestAI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str

@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")


@app.get("/health")
def health():
    return {"status": "ok", "service": "OrchestAI"}


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
        return [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "due_date": str(t.due_date)
            }
            for t in tasks
        ]