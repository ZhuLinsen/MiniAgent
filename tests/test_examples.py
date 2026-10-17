"""Native examples can be imported without parsing args or making API calls."""
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
