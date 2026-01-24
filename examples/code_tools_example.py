#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Quick smoke test for code tools.

This example is runnable directly from the repo without installing the package.
"""

import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miniagent.tools.code_tools import read, write, edit, glob, grep, bash


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        f = root / "hello.txt"

        print(write(str(f), "a\nb\nc\n"))
        print(read(str(f), offset=1, limit=5))
        print(edit(str(f), "b", "B", all=False))
        print(read(str(f), offset=1, limit=5))

        (root / "sub").mkdir()
        (root / "sub" / "x.py").write_text("print('hi')\n# TODO\n", encoding="utf-8")

        print(glob("**/*.py", path=str(root)))
        print(grep("TODO", path=str(root)))
        print(bash("echo miniagent"))


if __name__ == "__main__":
    main()
