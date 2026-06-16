from __future__ import annotations
from pathlib import Path
EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".log", ".err", ".sqlite", ".db", ".png", ".jpg", ".jpeg", ".gif", ".zip"}

def export_project_prompt(root: str = ".", output: str = "FIS_PROJECT_CONTEXT.md") -> dict:
    root_path = Path(root).resolve(); out_path = Path(output)
    chunks = [f"# FIS Project Context\n\nRoot: `{root_path}`\n"]
    count = 0
    for path in sorted(root_path.rglob("*")):
        if not path.is_file() or any(part in EXCLUDED_DIRS for part in path.parts) or path.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        try: text = path.read_text(encoding="utf-8", errors="ignore")[:12000]
        except OSError: continue
        rel = path.relative_to(root_path)
        chunks.append(f"\n## {rel}\n\n```text\n{text}\n```\n")
        count += 1
    out_path.write_text("".join(chunks), encoding="utf-8")
    return {"ok": True, "output": str(out_path), "files": count}
if __name__ == "__main__": print(export_project_prompt())
