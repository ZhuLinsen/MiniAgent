"""Minimal MiniAgent example — copy this to get started!

Before running:
  1. Copy .env.example to .env in your project directory
  2. Fill in LLM_API_KEY, LLM_MODEL, and LLM_API_BASE
  3. Run: python minimal_example.py
"""

import os
import sys
from dotenv import load_dotenv
from miniagent import MiniAgent

load_dotenv()

api_key = os.getenv("LLM_API_KEY")
if not api_key:
    print("Error: LLM_API_KEY not found.")
    print("Please copy .env.example to .env and fill in your API key.")
    sys.exit(1)

agent = MiniAgent(
    model=os.getenv("LLM_MODEL", "deepseek-chat"),
    api_key=api_key,
    base_url=os.getenv("LLM_API_BASE"),
)
agent.load_all_tools()

result = agent.run("What is 42 * 1337? Use the calculator tool.")
print(result)
