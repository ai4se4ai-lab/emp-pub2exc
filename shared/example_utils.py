"""
Utilities for resolving example fixtures under tests/examples/.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExampleContext:
    example_dir: Path
    paper_path: Path
    repo_txt_path: Path | None
    repo_url: str | None


def list_example_dirs(root: Path | None = None) -> list[Path]:
    base = root or Path("tests/examples")
    if not base.exists():
        return []
    return sorted(path for path in base.iterdir() if path.is_dir())


def resolve_example_context(example_dir: str | Path) -> ExampleContext:
    path = Path(example_dir)
    if not path.exists():
        raise FileNotFoundError(
            f"Example directory not found: {path}. "
            "Did you mean a path under tests/examples/?"
        )
    if not path.is_dir():
        raise NotADirectoryError(f"Expected an example directory, got: {path}")

    md_files = sorted(
        candidate
        for candidate in path.glob("*.md")
        if candidate.is_file() and candidate.name.lower() != "readme.md"
    )
    if not md_files:
        raise FileNotFoundError(f"No Markdown paper found in example directory: {path}")
    if len(md_files) > 1:
        names = ", ".join(file.name for file in md_files)
        raise ValueError(
            f"Expected exactly one Markdown paper in {path}, found multiple: {names}"
        )

    repo_txt_path = path / "repo.txt"
    repo_url = None
    if repo_txt_path.exists():
        raw = repo_txt_path.read_text(encoding="utf-8").strip()
        repo_url = raw or None

    return ExampleContext(
        example_dir=path,
        paper_path=md_files[0],
        repo_txt_path=repo_txt_path if repo_txt_path.exists() else None,
        repo_url=repo_url,
    )
