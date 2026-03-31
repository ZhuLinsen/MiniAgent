"""Minimal MiniAgent example — copy this to get started!"""

import os
from dotenv import load_dotenv
from miniagent import MiniAgent

load_dotenv()

agent = MiniAgent(
    model=os.getenv("LLM_MODEL", "deepseek-chat"),
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_API_BASE"),
)
agent.load_all_tools()

result = agent.run("What is 42 * 1337? Use the calculator tool.")
print(result)
