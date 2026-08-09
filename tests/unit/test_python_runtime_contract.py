from pathlib import Path
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON_314_DIGEST = (
    "python@sha256:a7fb1e634c4a578f9e0bd6327f11a3cde11b7a9395f48e24360c0988bcc5c2bc"
)


def test_project_metadata_targets_python_314() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["requires-python"] == ">=3.14"
    assert pyproject["tool"]["black"]["target-version"] == ["py314"]


def test_github_python_jobs_use_python_314() -> None:
    workflow_paths = [
        PROJECT_ROOT / ".github" / "workflows" / "ci.yml",
        PROJECT_ROOT / ".github" / "workflows" / "pr7-block3-proof.yml",
    ]

    for workflow_path in workflow_paths:
        source = workflow_path.read_text(encoding="utf-8")
        assert "python-version: '3.11'" not in source
        assert "python-version: '3.14'" in source


def test_runtime_container_pin_matches_python_314_artifact_lock() -> None:
    dockerfiles = [
        PROJECT_ROOT / "Dockerfile",
        PROJECT_ROOT / "Dockerfile.bridge",
    ]
    lock_files = [
        PROJECT_ROOT / "docs" / "project-ops" / "pr7-block3-artifact-lock.json",
        PROJECT_ROOT / "docs" / "project-ops" / "pr7-block3bc-artifact-lock.json",
    ]

    for dockerfile in dockerfiles:
        assert dockerfile.read_text(encoding="utf-8").splitlines()[0] == (
            f"FROM {PYTHON_314_DIGEST}"
        )

    for lock_file in lock_files:
        assert PYTHON_314_DIGEST in lock_file.read_text(encoding="utf-8")


def test_backend_uses_cpu_torch_index_for_container_runtime() -> None:
    dockerfile = PROJECT_ROOT / "Dockerfile"

    source = dockerfile.read_text(encoding="utf-8")

    assert "https://download.pytorch.org/whl/cpu" in source
