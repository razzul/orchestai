# agents/task_agent.py
import google.generativeai as genai
from db.database import AsyncSessionLocal
from db.models import Task, ExecutionLog
from datetime import datetime
import os, json

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


async def create_task(user_id: str, title: str, due_date: str = None, priority: str = "medium") -> dict:
    async with AsyncSessionLocal() as db:
        task = Task(
            user_id=user_id,
            title=title,
            due_date=datetime.fromisoformat(due_date) if due_date else None,
            priority=priority,
            status="pending"
        )
        db.add(task)
        log = ExecutionLog(agent="TaskAgent", action="create_task", status="success")
        db.add(log)
        await db.commit()
        return {"task_id": str(task.id), "title": title, "status": "created"}


async def list_tasks(user_id: str) -> list:
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Task).where(Task.user_id == user_id))
        tasks = result.scalars().all()
        return [{"id": str(t.id), "title": t.title, "status": t.status, "priority": t.priority} for t in tasks]


async def update_task_status(task_id: str, status: str) -> dict:
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            task.status = status
            await db.commit()
            return {"task_id": task_id, "new_status": status}
        return {"error": "Task not found"}


async def run_task_agent(user_id: str, instruction: str) -> str:
    """Uses Gemini to decide which task operation to perform."""
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""
    You are a task manager. The user said: "{instruction}"
    User ID: {user_id}

    Based on the instruction, respond ONLY with a JSON object like:
    {{"action": "create_task", "title": "...", "due_date": "YYYY-MM-DD", "priority": "high/medium/low"}}
    OR
    {{"action": "list_tasks"}}
    OR
    {{"action": "update_task_status", "task_id": "...", "status": "completed"}}
    """
    response = model.generate_content(prompt)
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)

    if data["action"] == "create_task":
        result = await create_task(user_id, data["title"], data.get("due_date"), data.get("priority", "medium"))
        return f"Task created: {result['title']}"
    elif data["action"] == "list_tasks":
        tasks = await list_tasks(user_id)
        return f"Your tasks: {json.dumps(tasks)}"
    elif data["action"] == "update_task_status":
        result = await update_task_status(data["task_id"], data["status"])
        return f"Task updated: {result}"
    return "Task operation completed."