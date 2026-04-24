"""Tests for example directory resolution helpers."""
from pathlib import Path

import pytest

from shared.example_utils import list_example_dirs, resolve_example_context


def test_resolve_example_context_reads_markdown_and_repo(tmp_path):
    example_dir = tmp_path / "tests" / "examples" / "KGTN-en"
    example_dir.mkdir(parents=True)
    paper = example_dir / "KGTN-en.md"
    paper.write_text("# Paper")
    (example_dir / "repo.txt").write_text("https://github.com/example/repo")

    context = resolve_example_context(example_dir)

    assert context.paper_path == paper
    assert context.repo_url == "https://github.com/example/repo"


def test_resolve_example_context_rejects_multiple_markdown_files(tmp_path):
    example_dir = tmp_path / "tests" / "examples" / "sample"
    example_dir.mkdir(parents=True)
    (example_dir / "paper-a.md").write_text("# A")
    (example_dir / "paper-b.md").write_text("# B")

    with pytest.raises(ValueError):
        resolve_example_context(example_dir)


def test_list_example_dirs_returns_directories_only(tmp_path):
    root = tmp_path / "tests" / "examples"
    (root / "a").mkdir(parents=True)
    (root / "b").mkdir()
    (root / "ignore.txt").write_text("x")

    dirs = list_example_dirs(root)

    assert [path.name for path in dirs] == ["a", "b"]
