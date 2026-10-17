"""Create a deliberately broken, isolated coding-demo fixture; never overwrites."""
import argparse
from pathlib import Path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    args.workspace.mkdir(parents=True, exist_ok=False)
    (args.workspace / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (args.workspace / "test_calculator.py").write_text(
        "import unittest\nfrom calculator import add\n\n"
        "class AddTests(unittest.TestCase):\n"
        "    def test_add(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n"
        "        self.assertEqual(add(-1, 1), 0)\n\n"
        "if __name__ == '__main__':\n    unittest.main()\n", encoding="utf-8")
    print(f"Created fixture in {args.workspace}; baseline test is expected to fail.")
