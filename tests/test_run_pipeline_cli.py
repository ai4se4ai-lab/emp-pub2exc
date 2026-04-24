"""Tests for scripts.run_pipeline CLI resolution."""
import sys

from scripts import run_pipeline as pipeline_script


def test_run_pipeline_main_resolves_example_dir(tmp_path, monkeypatch):
    example_dir = tmp_path / "tests" / "examples" / "KGTN-en"
    example_dir.mkdir(parents=True)
    paper_path = example_dir / "KGTN-en.md"
    paper_path.write_text("# Paper")
    (example_dir / "repo.txt").write_text("https://github.com/example/repo")

    captured = {}

    def fake_run_pipeline(paper_path_arg, skip_hitl_arg, start_from_arg):
        captured["paper_path"] = paper_path_arg
        captured["skip_hitl"] = skip_hitl_arg
        captured["start_from"] = start_from_arg
        return "run-id"

    monkeypatch.setattr(pipeline_script, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_pipeline.py", "--example-dir", str(example_dir), "--skip-hitl"],
    )

    pipeline_script.main()

    assert captured["paper_path"] == paper_path
    assert captured["skip_hitl"] is True
    assert captured["start_from"] == "paper_analyst"
