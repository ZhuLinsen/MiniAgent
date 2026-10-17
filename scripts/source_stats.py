"""Reproducible physical/nonempty source counts (no trailing phantom line)."""
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
tracked = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "miniagent"], cwd=root, text=True).splitlines()
files = sorted(root / name for name in tracked if name.endswith(".py"))
counts = {str(p.relative_to(root)): p.read_text(encoding="utf-8").splitlines() for p in files}
core = ["agent.py", "harness.py", "llm.py", "tools/registry.py"]
mechanisms = core + ["policy.py", "plugins.py", "session.py"]
print(json.dumps({
    "core_physical": sum(len((root / "miniagent" / name).read_text(encoding="utf-8").splitlines()) for name in core),
    "core_files": core,
    "runtime_mechanisms_physical": sum(len((root / "miniagent" / name).read_text(encoding="utf-8").splitlines()) for name in mechanisms),
    "runtime_mechanisms_files": mechanisms,
    "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
    "files": len(files),
    "physical": sum(len(lines) for lines in counts.values()),
    "nonempty": sum(bool(line.strip()) for lines in counts.values() for line in lines),
    "per_file": {name: len(lines) for name, lines in counts.items()},
}, indent=2))
