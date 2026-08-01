from pathlib import Path


def test_backend_ci_installs_training_dependencies_before_full_suite() -> None:
    workflow = (
        Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"
    )
    source = workflow.read_text(encoding="utf-8")
    backend_job = source.split("  postgres:", 1)[0]

    assert "pip install -r requirements.txt" in backend_job
    assert "pip install -r requirements.train.txt" in backend_job
