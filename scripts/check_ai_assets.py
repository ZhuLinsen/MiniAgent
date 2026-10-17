"""Check the repository's single instruction source and review entry points."""
from pathlib import Path
import subprocess


def main():
    root = Path(__file__).resolve().parents[1]
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    principles = ("核心简单", "DSH 常用能力", "易用美观", "便于传播")
    errors = [f"AGENTS.md is missing: {text}" for text in (*principles, "每次 Codex 运行") if text not in agents]
    template = (root / ".github/PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    if "AGENTS.md" not in template or any(text not in template for text in principles):
        errors.append("PR template must reference the four project principles")
    claude = root / "CLAUDE.md"
    indexed = subprocess.check_output(["git", "ls-files", "--stage", "--", "CLAUDE.md"],
                                      cwd=root, text=True)
    if claude.is_symlink():
        valid = claude.readlink() == Path("AGENTS.md")
    elif claude.is_file():
        valid = indexed.startswith("120000 ") and claude.read_text(encoding="utf-8").strip() == "AGENTS.md"
    else:
        valid = False
    if not valid:
        errors.append("CLAUDE.md must be a Git symlink to AGENTS.md")
    if errors:
        raise SystemExit("\n".join(errors))
    print("AI assets passed: AGENTS.md is the single source; four principles and PR entry are present.")


if __name__ == "__main__":
    main()
