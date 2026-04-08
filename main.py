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

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests
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

@app.on_event("startup")
async def startup_event():
    from db.database import engine
    from db.models import Base
    from sqlalchemy import text
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS title VARCHAR;"))
        except Exception as e:
            print(f"Schema update error: {e}")


class AuthRequest(BaseModel):
    credential: str


@app.post("/auth/google")
async def auth_google(req: AuthRequest):
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id or client_id == "your-google-client-id.apps.googleusercontent.com":
        # Fallback for development if CLIENT_ID is not set, 
        # but in production this should fail if not configured.
        print("Warning: GOOGLE_CLIENT_ID not configured properly.")
        # We can't verify, but for the sake of the demo, maybe we just decode?
        # Better to return error if it's meant to be secure.
        pass

    try:
        # Verify the ID token
        idinfo = id_token.verify_oauth2_token(req.credential, requests.Request(), client_id)
        
        user_id = idinfo['sub']
        email = idinfo['email']
        name = idinfo.get('name')
        picture = idinfo.get('picture')
        
        async with AsyncSessionLocal() as db:
            from db.models import User
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                user = User(id=user_id, email=email, name=name, picture=picture)
                db.add(user)
                await db.commit()
            else:
                user.name = name
                user.picture = picture
                await db.commit()
                
        return {"user_id": user_id, "email": email, "name": name, "picture": picture}
    except Exception as e:
        print(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail=str(e))


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

@app.get("/sessions")
async def get_sessions(user_id: str):
    from db.models import UserSession
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserSession).where(UserSession.user_id == user_id).order_by(UserSession.created_at.desc()))
        sessions = result.scalars().all()
        return [{"session_id": s.session_id, "title": s.title or "New Chat", "created_at": str(s.created_at)} for s in sessions]

@app.get("/sessions/{session_id}")
async def get_session_history(session_id: str):
    from db.models import UserSession
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserSession).where(UserSession.session_id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"history": session.history, "title": session.title or "New Chat", "created_at": str(session.created_at)}

class TitleUpdateRequest(BaseModel):
    title: str

@app.put("/sessions/{session_id}/title")
async def update_session_title_endpoint(session_id: str, req: TitleUpdateRequest):
    from db.models import UserSession
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserSession).where(UserSession.session_id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session.title = req.title
        await db.commit()
        return {"status": "ok", "title": session.title}

@app.delete("/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    from db.models import UserSession, ExecutionLog
    from sqlalchemy import delete
    async with AsyncSessionLocal() as db:
        # Delete related logs
        await db.execute(delete(ExecutionLog).where(ExecutionLog.session_id == session_id))
        # Delete session
        result = await db.execute(select(UserSession).where(UserSession.session_id == session_id))
        session = result.scalar_one_or_none()
        if not session:
             raise HTTPException(status_code=404, detail="Session not found")
        await db.delete(session)
        await db.commit()
        return {"status": "ok", "message": "Session deleted"}


@app.get("/logs")
async def get_logs(session_id: str = None):
    from db.models import ExecutionLog
    async with AsyncSessionLocal() as db:
        query = select(ExecutionLog).order_by(ExecutionLog.timestamp.desc())
        if session_id:
            query = query.where(ExecutionLog.session_id == session_id)
        result = await db.execute(query)
        logs = result.scalars().all()
        return [{"id": str(log.id), "session_id": log.session_id, "agent": log.agent, "action": log.action, "status": log.status, "timestamp": str(log.timestamp)} for log in logs]

@app.get("/calendar/events")
def get_calendar_events(date: str):
    try:
        from tools.calendar_mcp import list_calendar_events
        events = list_calendar_events(date)
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))