"""Opt-in, bounded real-model read/edit/test demo in a disposable fixture."""
import argparse
import asyncio
from functools import partial
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from miniagent import Harness, Plugin
from miniagent.config import load_config
from miniagent.llm import LLMBackend
from miniagent.plugins import coding_tools
from miniagent.policy import Policy


async def demo(args):
    cfg = load_config(args.config, model_override=args.model)
    if not cfg.llm.model:
        raise ValueError("Select --model provider:model-id or configure LLM_MODEL")
    backend = LLMBackend(cfg.llm.model, providers=cfg.providers, api_key=cfg.llm.api_key,
                         base_url=cfg.llm.api_base, temperature=0, timeout=30)
    limits = {"max_completion_tokens": 512} if backend.provider == "openai" else {"max_tokens": 256}
    backend.client.acompletion = partial(backend.client.acompletion, **limits)
    trace, usage = [], []
    started = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix="miniagent-coding-") as folder:
            root = Path(folder)
            (root / "calc.py").write_text("def add(a, b):\n    return a - b\n")
            test = "from calc import add\nassert add(2, 3) == 5\nprint('TEST PASSED')\n"
            (root / "test_calc.py").write_text(test)
            app = Harness(backend, policy=Policy(folder, mode="trusted"),
                          system_prompt="Follow the requested tool steps. Keep the final answer short.")
            app.use(coding_tools())
            def observe(ctx):
                ctx.on("tool.end", lambda e: trace.append({"name": e["name"], "error": bool(e["error"])}))
                ctx.on("llm.response", lambda e: usage.append(e.get("usage") or {}))
            app.use(Plugin("demo-observer", observe))
            command = json.dumps(sys.executable) + " test_calc.py"
            async with app:
                await app.arun("Read calc.py, fix add to use addition with edit, then use bash to run: "
                               + command + ". Do not change test_calc.py. Report the result.", max_steps=6)
            tested = subprocess.run([sys.executable, "test_calc.py"], cwd=root,
                                    capture_output=True, timeout=10)
            passed = (tested.returncode == 0 and (root / "test_calc.py").read_text() == test
                      and {"read", "edit", "bash"} <= {t["name"] for t in trace}
                      and any(m.get("role") == "tool" and "TEST PASSED" in m.get("content", "")
                              for m in app.messages))
            report = {"model": cfg.llm.model, "passed": passed, "tool_events": trace,
                      "usage": usage, "seconds": round(time.perf_counter() - started, 3)}
    finally:
        await backend.aclose()
    print(json.dumps(report))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="provider:model-id; otherwise use configuration")
    parser.add_argument("--config", help="JSON provider configuration")
    parser.add_argument("--report", type=Path)
    try:
        sys.exit(asyncio.run(demo(parser.parse_args())))
    except Exception as error:
        print(f"Coding smoke failed: {type(error).__name__}", file=sys.stderr)
        sys.exit(1)
