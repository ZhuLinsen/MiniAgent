"""Record the real CLI as text and SVG; never substitutes a model response.

Requires the installed project (pip install -e .). Arguments after -- go to the
normal CLI. Input, configuration and provider calls retain their usual behavior.
"""
import argparse
import os
from pathlib import Path
from unittest.mock import patch

from rich.console import Console
from rich.terminal_theme import MONOKAI

from miniagent.cli import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Output stem; writes .svg and .txt")
    parser.add_argument("--width", type=int, default=100)
    parser.add_argument("args", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    console = Console(record=True, force_terminal=True, color_system="truecolor", width=options.width)
    argv = options.args[1:] if options.args[:1] == ["--"] else options.args
    # Only the output sink changes. Backend, tools, policy and session are real.
    with patch("miniagent.cli_runtime.Console", return_value=console):
        status = main(argv)
    transcript = "\n".join(line.rstrip() for line in console.export_text(clear=False).splitlines()) + "\n"
    secrets = [value for key, value in os.environ.items() if key.endswith("API_KEY") and len(value) > 8]
    if any(secret in transcript for secret in secrets):
        raise SystemExit("Capture contains a credential; no files written")
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.with_suffix(".txt").write_text(transcript, encoding="utf-8")
    svg = console.export_svg(title="MiniAgent · actual CLI output", theme=MONOKAI)
    svg = svg.replace("font-family: Fira Code, monospace;", "font-family: Consolas, 'Liberation Mono', monospace;")
    # Match Rich's 12.2px cell with Consolas (0.55em); avoids remote web fonts.
    svg = svg.replace("font-size: 20px;", "font-size: 22.1818px;")
    options.output.with_suffix(".svg").write_text("\n".join(line.rstrip() for line in svg.splitlines()) + "\n", encoding="utf-8")
    raise SystemExit(status)
