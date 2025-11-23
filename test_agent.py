import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from backend.agent import run_agent

async def main():
    query = "Who is the present CM of Telangana state?"
    print(f"Running query: {query}")
    response = await run_agent(query)
    print("\nFinal Response:")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
