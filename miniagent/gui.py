"""MiniAgent Tkinter GUI.

A minimal desktop assistant UI (no extra dependencies).
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import scrolledtext
from typing import Any, Dict, Optional

from .agent import MiniAgent
from .config import load_config
from .memory import Memory


class _App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MiniAgent")
        self.geometry("800x600")

        self._out = scrolledtext.ScrolledText(self, wrap=tk.WORD, state=tk.DISABLED)
        self._out.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        bottom = tk.Frame(self)
        bottom.pack(fill=tk.X, padx=8, pady=(0, 8))

        self._entry = tk.Entry(bottom)
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._entry.bind("<Return>", lambda _e: self._on_send())

        self._send_btn = tk.Button(bottom, text="Send", command=self._on_send)
        self._send_btn.pack(side=tk.RIGHT, padx=(8, 0))

        self._ui_queue: "queue.Queue[str]" = queue.Queue()
        self._agent, self._memory = self._build_agent()

        self.after(50, self._drain_queue)
        self._append("MiniAgent GUI ready. Type and press Enter.\n")

    def _append(self, text: str) -> None:
        self._out.configure(state=tk.NORMAL)
        self._out.insert(tk.END, text)
        self._out.see(tk.END)
        self._out.configure(state=tk.DISABLED)

    def _drain_queue(self) -> None:
        try:
            while True:
                msg = self._ui_queue.get_nowait()
                self._append(msg)
        except queue.Empty:
            pass
        self.after(50, self._drain_queue)

    def _build_agent(self) -> tuple[MiniAgent, Memory]:
        cfg = load_config(None)

        api_key = cfg.llm.api_key
        if not api_key:
            raise RuntimeError("Missing API key. Set LLM_API_KEY in environment.")

        memory = Memory()
        memory.load()

        system_prompt = cfg.system_prompt
        mem_ctx = memory.context()
        if mem_ctx:
            system_prompt = system_prompt.rstrip() + "\n\n" + mem_ctx

        agent = MiniAgent(
            model=cfg.llm.model,
            api_key=api_key,
            base_url=cfg.llm.api_base,
            temperature=cfg.llm.temperature,
            system_prompt=system_prompt,
            use_reflector=cfg.enable_reflection,
        )

        agent.tools = []
        tools = cfg.default_tools or agent.get_available_tools()
        for tool_name in tools:
            agent.load_builtin_tool(tool_name)

        return agent, memory

    def _tool_callback(self, event: str, name: str, payload: Dict[str, Any]) -> None:
        if event == "start":
            self._ui_queue.put(f"[tool] {name} {payload}\n")
        elif event == "end":
            self._ui_queue.put(f"[tool] {name} -> {payload.get('result')}\n")

    def _on_send(self) -> None:
        text = self._entry.get().strip()
        if not text:
            return
        self._entry.delete(0, tk.END)

        self._append(f"you> {text}\n")
        self._memory.push("user", text)

        def worker() -> None:
            try:
                try:
                    reply = self._agent.run_with_tools(text, tool_callback=self._tool_callback)
                except TypeError:
                    reply = self._agent.run(text)
                self._memory.push("assistant", reply)
                self._ui_queue.put(f"assistant> {reply}\n\n")
            except Exception as e:
                self._ui_queue.put(f"error: {e}\n\n")

        threading.Thread(target=worker, daemon=True).start()


def main() -> int:
    app = _App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
