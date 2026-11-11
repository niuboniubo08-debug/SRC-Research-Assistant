"""Generate a deterministic project tree for acceptance evidence."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
OUTPUT = ROOT / "docs" / "acceptance" / "project_tree.txt"
SKIP_NAMES = {
    ".venv",
    "__pycache__",
    ".tmp",
    ".pytest_cache",
    ".screenshot-demo",
    "cache",
    "debug.log",
    "tmp",
}
SKIP_PREFIXES = ("pytest-of-", "pytest-cache-", "src-assistant-shot-")


def visible_children(directory: Path) -> list[Path]:
    children = []
    for child in directory.iterdir():
        if child.name in SKIP_NAMES or child.name.startswith(SKIP_PREFIXES):
            continue
        if child.name.endswith((".pyc", ".pyo")):
            continue
        children.append(child)
    return sorted(children, key=lambda item: (item.is_file(), item.name.lower()))


def render(directory: Path, prefix: str = "") -> list[str]:
    lines: list[str] = []
    children = visible_children(directory)
    for index, child in enumerate(children):
        last = index == len(children) - 1
        connector = "└── " if last else "├── "
        suffix = "/" if child.is_dir() else ""
        marker = ""
        relative = child.relative_to(ROOT).as_posix()
        if relative == "main.py":
            marker = "   [实际入口]"
        elif relative == "storage/src_research.db":
            marker = "   [主数据库]"
        elif relative == "config.yaml":
            marker = "   [配置]"
        lines.append(f"{prefix}{connector}{child.name}{suffix}{marker}")
        if child.is_dir():
            extension = "    " if last else "│   "
            lines.extend(render(child, prefix + extension))
    return lines


def main() -> int:
    lines = [
        "D:\\挖漏洞\\",
        "├── .venv/   [独立 Python 虚拟环境；第三方依赖目录树未展开]",
        "└── SRC-Research-Assistant/",
    ]
    lines.extend(render(ROOT, "    "))

    def included_files() -> list[Path]:
        result = []
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT)
            if any(part in SKIP_NAMES for part in relative.parts):
                continue
            if any(part.startswith(SKIP_PREFIXES) for part in relative.parts):
                continue
            if path.suffix.lower() in {".pyc", ".pyo"}:
                continue
            result.append(path)
        return result

    files = included_files()
    text = "\n".join(lines) + "\n"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"TOTAL_FILES={len(files)}")
    print(f"TREE_FILE={OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
