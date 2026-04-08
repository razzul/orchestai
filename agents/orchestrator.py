# agents/orchestrator.py
import google.generativeai as genai
from agents.task_agent import run_task_agent
from agents.calendar_agent import run_calendar_agent
from agents.comms_agent import run_comms_agent
from db.database import AsyncSessionLocal
from db.models import UserSession, ExecutionLog
from sqlalchemy import select
import os, json

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


async def get_or_create_session(session_id: str, user_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserSession).where(UserSession.session_id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            session = UserSession(session_id=session_id, user_id=user_id, history=[], title="New Chat")
            db.add(session)
            await db.commit()
            return [], "New Chat"
        return session.history, session.title


async def save_session(session_id: str, history: list):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserSession).where(UserSession.session_id == session_id))
        session = result.scalar_one_or_none()
        if session:
            session.history = history
            await db.commit()

async def update_session_title(session_id: str, title: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserSession).where(UserSession.session_id == session_id))
        session = result.scalar_one_or_none()
        if session:
            session.title = title
            await db.commit()

async def save_execution_logs(session_id: str, actions: list):
    async with AsyncSessionLocal() as db:
        for action in actions:
            log = ExecutionLog(
                session_id=session_id,
                agent=action["agent"],
                action=action["action"],
                status=action["status"]
            )
            db.add(log)
        await db.commit()


async def run_orchestrator(user_id: str, session_id: str, message: str) -> dict:
    history, title = await get_or_create_session(session_id, user_id)
    new_title = title

    # Step 1: Decide which agents are needed
    model = genai.GenerativeModel("gemini-2.0-flash")
    routing_prompt = f"""
    You are OrchestAI, a productivity orchestrator.
    User message: "{message}"

    Which agents are needed? Respond ONLY with a JSON like:
    {{"agents": ["task", "calendar", "comms"], "reasoning": "brief reason"}}

    Available agents: "task" (for to-dos and task management), "calendar" (for scheduling events), "comms" (for emails)
    Only include agents that are actually needed.
    """
    try:
        routing_response = model.generate_content(routing_prompt)
        raw = routing_response.text.strip().replace("```json", "").replace("```", "").strip()
        routing = json.loads(raw)
    except Exception as e:
        print(f"Routing error: {e}")
        routing = {"agents": [], "reasoning": "Fallback due to routing error"}
    
    agents_needed = routing.get("agents", [])
    intent_map = {"task": "create task", "calendar": "create_event", "comms": "send_email"}
    intent_str = " + ".join([intent_map.get(a, a) for a in agents_needed])
    
    # actions_taken will hold detailed logs for the Activity Panel
    actions_taken = [{"agent": "Orchestrator", "action": f"Intent: {intent_str}", "status": "ROUTED"}]
    # display_tags will hold clean labels for the AI message bubble
    display_tags = []
    
    results = []

    # Step 2: Run each needed agent
    if "task" in agents_needed:
        agent_resp = await run_task_agent(user_id, message, history)
        results.append(agent_resp["response"])
        actions_taken.append({"agent": "TaskAgent", "action": agent_resp["log_entry"], "status": "200 OK"})
        display_tags.append({"label": agent_resp.get('tag_label', 'Task created'), "agent": "TaskAgent"})

    if "calendar" in agents_needed:
        agent_resp = await run_calendar_agent(message, history)
        results.append(agent_resp["response"])
        actions_taken.append({"agent": "CalendarAgent", "action": agent_resp["log_entry"], "status": "200 OK"})
        display_tags.append({"label": agent_resp.get('tag_label', 'Event created'), "agent": "CalendarAgent"})

    if "comms" in agents_needed:
        agent_resp = await run_comms_agent(message, history)
        results.append(agent_resp["response"])
        # Use CommAgent (singular) for the display if requested by wireframe
        actions_taken.append({"agent": "CommAgent", "action": agent_resp["log_entry"], "status": "200 OK"})
        display_tags.append({"label": agent_resp.get('tag_label', 'Email sent'), "agent": "CommAgent"})

    # Step 3: Synthesize final response
    synthesis_prompt = f"""
    The user asked: "{message}"
    The following actions were completed: {json.dumps(results)}
    Write a short, friendly summary of what was done for the user.
    """
    try:
        final_response_res = model.generate_content(synthesis_prompt)
        # Use simple prefix if synthesis succeeded
        final_text = "All done! Here's what I executed:\n" + final_response_res.text.strip()
    except Exception as e:
        print(f"Synthesis error: {e}")
        final_text = "All done! Here's what I executed:"

    # Generate title if it's a "New Chat"
    if title == "New Chat":
        try:
            title_prompt = f"Generate a very short (max 5 words) descriptive title for this conversation based on this first message: '{message}'. Respond ONLY with the title string."
            title_res = model.generate_content(title_prompt)
            new_title = title_res.text.strip()
            await update_session_title(session_id, new_title)
        except Exception as e:
            print(f"Title generation error: {e}")
            new_title = "New Chat"

    # Save to session history
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": final_text})
    await save_session(session_id, history)
    await save_execution_logs(session_id, actions_taken)

    return {
        "response": final_text,
        "actions_taken": actions_taken,
        "display_tags": display_tags,
        "title": new_title
    }