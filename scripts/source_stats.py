"""Reproducible physical/nonempty source counts (no trailing phantom line)."""
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = sorted((root / "miniagent").rglob("*.py"))
counts = {str(p.relative_to(root)): p.read_text(encoding="utf-8").splitlines() for p in files}
print(json.dumps({
    "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
    "files": len(files),
    "physical": sum(len(lines) for lines in counts.values()),
    "nonempty": sum(bool(line.strip()) for lines in counts.values() for line in lines),
    "per_file": {name: len(lines) for name, lines in counts.items()},
}, indent=2))
