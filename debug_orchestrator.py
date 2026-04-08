
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from agents.orchestrator import run_orchestrator

async def main():
    try:
        user_id = "test_user"
        session_id = "test_sess"
        message = "Create a task for the budget review, schedule 90 min on Thursday, and email Sarah the agenda"
        print(f"Testing with message: {message}")
        result = await run_orchestrator(user_id, session_id, message)
        print("Success!")
        print(result)
    except Exception as e:
        print("Error:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
