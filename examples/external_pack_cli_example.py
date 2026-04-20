#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
External Pack CLI Startup Example

Demonstrates the complete MiniAgent startup flow when using an external pack.

Usage:
    export LLM_API_KEY=your_api_key
    export LLM_MODEL=deepseek-chat
    export LLM_API_BASE=https://api.deepseek.com/v1
    python examples/external_pack_cli_example.py

Optional:
    python examples/external_pack_cli_example.py --run

Copy/paste commands:
    python -m miniagent --pack examples.miniagent_demo_pack --skill demo_operator --tool read --tool grep --tool bash --tool demo_customer_lookup
    python -m miniagent --config examples/config_example.json --profile demo_ops
    python -m miniagent --config examples/config_example.json --profile demo_ops --strict-resolution

If you installed the console entry point:
    miniagent --pack examples.miniagent_demo_pack --skill demo_operator --tool read --tool grep --tool bash --tool demo_customer_lookup
    miniagent --config examples/config_example.json --profile demo_ops
    miniagent --config examples/config_example.json --profile demo_ops --strict-resolution
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "examples" / "config_example.json"
PACK_MODULE = "examples.miniagent_demo_pack"


def _format_command(parts: List[str]) -> str:
    """Render a shell-safe command string."""

    return " ".join(shlex.quote(part) for part in parts)


def build_commands() -> Dict[str, List[str]]:
    """Build the recommended CLI startup commands."""

    base = [sys.executable, "-m", "miniagent"]
    return {
        "ad_hoc": base + [
            "--pack", PACK_MODULE,
            "--skill", "demo_operator",
            "--tool", "read",
            "--tool", "grep",
            "--tool", "bash",
            "--tool", "demo_customer_lookup",
        ],
        "profile": base + [
            "--config", str(CONFIG_PATH),
            "--profile", "demo_ops",
        ],
        "strict": base + [
            "--config", str(CONFIG_PATH),
            "--profile", "demo_ops",
            "--strict-resolution",
        ],
    }


def print_guide() -> None:
    """Print the full startup flow for the demo external pack."""

    commands = build_commands()
    print("=== MiniAgent External Pack Startup ===")
    print()
    print("1. Prepare environment variables:")
    print("   export LLM_API_KEY=your_api_key")
    print("   export LLM_MODEL=deepseek-chat")
    print("   export LLM_API_BASE=https://api.deepseek.com/v1")
    print()
    print("2. Start with explicit CLI arguments:")
    print("   %s" % _format_command(commands["ad_hoc"]))
    print()
    print("3. Start with config + profile:")
    print("   %s" % _format_command(commands["profile"]))
    print()
    print("4. Enable strict bootstrap checks for deployment:")
    print("   %s" % _format_command(commands["strict"]))
    print()
    print("5. The same commands with the installed console script:")
    print("   miniagent --pack %s --skill demo_operator --tool read --tool grep --tool bash --tool demo_customer_lookup" % PACK_MODULE)
    print("   miniagent --config examples/config_example.json --profile demo_ops")
    print("   miniagent --config examples/config_example.json --profile demo_ops --strict-resolution")
    print()
    print("Pack module: %s" % PACK_MODULE)
    print("Config file: %s" % CONFIG_PATH)


def run_profile_command() -> int:
    """Optionally launch the profile-based startup command."""

    missing = [
        key for key in ("LLM_API_KEY", "LLM_MODEL", "LLM_API_BASE")
        if not os.environ.get(key)
    ]
    if missing:
        print("Missing environment variables: %s" % ", ".join(missing))
        print("Run without --run to print the commands only.")
        return 1

    command = build_commands()["profile"]
    print("Launching: %s" % _format_command(command))
    return subprocess.call(command, cwd=str(ROOT))


def main(argv: List[str] | None = None) -> int:
    """Entry point for the example."""

    argv = argv or sys.argv[1:]
    print_guide()

    if "--run" in argv:
        print()
        return run_profile_command()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
