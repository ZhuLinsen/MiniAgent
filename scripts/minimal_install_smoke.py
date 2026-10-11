"""Install a built wheel without extras and exercise it outside the checkout."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
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
    args = parser.parse_args()
    wheels = list((Path(__file__).resolve().parents[1] / "dist").glob("miniagent-*.whl"))
    if not args.uv or len(wheels) != 1:
        parser.error("uv and exactly one built MiniAgent wheel are required")
    with tempfile.TemporaryDirectory(prefix="miniagent-wheel-") as folder:
        root = Path(folder)
        venv.EnvBuilder(with_pip=False).create(root / "env")
        python = root / "env" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([args.uv, "pip", "install", "--python", str(python), str(wheels[0])], check=True)
        subprocess.run([str(python), "-I", "-c", SMOKE], cwd=root, check=True)
        subprocess.run([str(python), "-I", "-m", "miniagent", "--help"], cwd=root, check=True)
    print("Minimal installed-wheel smoke passed (no MCP or legacy extras).")


if __name__ == "__main__":
    main()
