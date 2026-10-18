"""Native examples can be imported without parsing args or making API calls."""
import asyncio
from pathlib import Path
import runpy

import pytest


@pytest.mark.parametrize("name", ["lean_harness", "custom_tools_example", "skill_example"])
def test_example_import_does_not_start_an_agent(name, monkeypatch):
    from miniagent import Harness
    def unexpected(*args, **kwargs):
        pytest.fail("Importing an example must not call a model")
    monkeypatch.setattr(Harness, "run", unexpected)
    path = Path(__file__).resolve().parents[1] / "examples" / f"{name}.py"
    module = runpy.run_path(str(path), run_name="example_import_check")
    assert callable(module["main"])


@pytest.mark.parametrize("source", ["example", "guide"])
def test_documented_calculator_executes_through_registry(source, tmp_path):
    from miniagent import Harness, Plugin, Policy
    root = Path(__file__).resolve().parents[1]
    app = Harness(policy=Policy(tmp_path, mode="readonly"))
    if source == "example":
        module = runpy.run_path(str(root / "examples/custom_tools_example.py"))
        app.use(Plugin("calculator", module["calculator"]))
    else:
        guide = (root / "docs/lean-harness.md").read_text(encoding="utf-8")
        snippet = next(block.split("```", 1)[0] for block in guide.split("```python\n")[1:]
                       if "def arithmetic(ctx):" in block.split("```", 1)[0])
        exec(snippet, {"app": app})
    async def scenario():
        async with app:
            assert await app.registry.execute("add_one", {"n": 2}, app.policy) == 3
        assert not app.registry.tools and not app.active
    asyncio.run(scenario())
