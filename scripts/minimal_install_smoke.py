"""Install a built wheel without extras and exercise it outside the checkout."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import statistics
import tempfile
import time
import venv

SMOKE = '''
import asyncio
import importlib.util
from pathlib import Path
from miniagent import Harness
from miniagent.plugins import coding_tools
from miniagent.policy import Policy

assert all(importlib.util.find_spec(name) is None for name in ("psutil", "requests", "mcp"))
class Backend:
    async def complete(self, messages, tools, stream):
        return {"role": "assistant", "content": "installed wheel works"}
async def main():
    Path("sample.txt").write_text("installed fixture")
    app = Harness(Backend(), policy=Policy(mode="readonly")).use(coding_tools())
    async with app:
        assert len(app.registry.schemas()) == 6
        assert "installed fixture" in await app.registry.execute("read", {"path": "sample.txt"}, app.policy)
        assert await app.arun("hello") == "installed wheel works"
        try:
            await app.registry.execute("write", {"path": "denied.txt", "content": "denied"}, app.policy)
        except PermissionError:
            pass
        else:
            raise AssertionError("readonly write was accepted")
    assert not Path("denied.txt").exists()
asyncio.run(main())
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uv", default=shutil.which("uv"))
    parser.add_argument("--report", type=Path, help="Save measured install size and startup timings as JSON")
    args = parser.parse_args()
    wheels = list((Path(__file__).resolve().parents[1] / "dist").glob("miniagent-*.whl"))
    if not args.uv or len(wheels) != 1:
        parser.error("uv and exactly one built MiniAgent wheel are required")
    with tempfile.TemporaryDirectory(prefix="miniagent-wheel-") as folder:
        root = Path(folder)
        venv.EnvBuilder(with_pip=False).create(root / "env")
        python = root / "env" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        started = time.perf_counter()
        subprocess.run([args.uv, "pip", "install", "--python", str(python), str(wheels[0])], check=True)
        install_seconds = time.perf_counter() - started
        subprocess.run([str(python), "-I", "-c", SMOKE], cwd=root, check=True)
        subprocess.run([str(python), "-I", "-m", "miniagent", "--help"], cwd=root, check=True)
        measurements = {}
        for name, command in (("import", ["-c", "import miniagent"]),
                              ("cli_help", ["-m", "miniagent", "--help"])):
            samples = []
            for _ in range(5):
                started = time.perf_counter()
                subprocess.run([str(python), "-I", *command], cwd=root, check=True,
                               stdout=subprocess.DEVNULL)
                samples.append(round(time.perf_counter() - started, 4))
            measurements[name] = {"seconds": samples, "median_seconds": statistics.median(samples)}
        site = root / "env" / ("Lib/site-packages" if os.name == "nt" else
                               f"lib/python{os.sys.version_info.major}.{os.sys.version_info.minor}/site-packages")
        report = {"platform": os.sys.platform, "python": os.sys.version.split()[0],
                  "wheel_bytes": wheels[0].stat().st_size,
                  "site_packages_bytes": sum(p.stat().st_size for p in site.rglob("*") if p.is_file()),
                  "install_seconds": round(install_seconds, 4), "startup": measurements}
        print(json.dumps(report))
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Minimal installed-wheel smoke passed (no MCP or legacy extras).")


if __name__ == "__main__":
    main()
