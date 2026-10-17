"""CLI entry point for the native Harness."""
import argparse
import asyncio
import sys

from . import __version__


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="miniagent")
    if "--legacy" in argv:
        parser.error("Text mode was retired in 0.3. Use the native CLI or the codex/legacy-pre-harness branch; see docs/legacy-migration.md.")
    parser.add_argument("--version", "-V", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", help="Configuration JSON")
    parser.add_argument("--connect", action="store_true", help="Configure a model interactively and exit")
    parser.add_argument("--model", help="provider:model-id")
    parser.add_argument("--api-key", help="Explicit selected-endpoint credential")
    parser.add_argument("--base-url", help="Explicit OpenAI-compatible endpoint")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--workspace", help="Managed file workspace (default current directory)")
    parser.add_argument("--allow-sensitive-files", action="store_true", help="Explicitly allow managed access to environment/key files and .git")
    parser.add_argument("--policy", choices=["readonly", "confirm", "trusted"], default="confirm")
    parser.add_argument("--session", help="Session JSONL path; existing sessions resume")
    parser.add_argument("--skill", help="Registered skill or SKILL.md path")
    parser.add_argument("--prompt", "-p", help="Run one noninteractive task")
    parser.add_argument("--no-stream", action="store_true")
    args = parser.parse_args(argv)
    from .logger import set_cli_mode
    set_cli_mode(True)
    from .cli_runtime import cli_run
    try:
        return asyncio.run(cli_run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
