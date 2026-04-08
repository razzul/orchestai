import asyncio
import os
import socket
import traceback
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from dotenv import load_dotenv
load_dotenv()

# 🔹 Set your DB URL here OR use env variable
DATABASE_URL = os.getenv("ALLOYDB_URL")
def parse_host_port(db_url: str):
    parsed = urlparse(db_url)
    return parsed.hostname, parsed.port or 5432

def check_tcp_connectivity(host: str, port: int, timeout: int = 3):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"

async def test_connection():
    print("🔍 Testing connection...")
    print("DB URL:", DATABASE_URL)
    if not DATABASE_URL:
        print("❌ Connection failed!")
        print("Error: ALLOYDB_URL is not set.")
        return

    host, port = parse_host_port(DATABASE_URL)
    reachable, reachability_error = check_tcp_connectivity(host, port)
    if not reachable:
        print(f"⚠️ TCP connectivity to {host}:{port} failed ({reachability_error})")
        print("   This usually means the database host is not reachable from your current network.")
        print("   For AlloyDB private IPs, connect from the same VPC/VPN or use the AlloyDB Auth Proxy.")

    engine = None

    try:
        engine = create_async_engine(
            DATABASE_URL,
            echo=True,
            connect_args={"timeout": 10}
        )

        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ Connection successful!")
            print("Result:", result.scalar())

    except Exception as e:
        print("❌ Connection failed!")
        print("Error type:", type(e).__name__)
        print("Error repr:", repr(e))
        print("Traceback:")
        traceback.print_exc()
    finally:
        if engine is not None:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_connection())