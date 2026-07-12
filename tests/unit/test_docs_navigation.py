from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CURRENT_DOCS = (
    Path("docs/README.md"),
    Path("docs/CONTEXT.md"),
    Path("docs/SETUP.md"),
    Path("docs/architecture.md"),
    Path("docs/project-ops/README.md"),
    Path("docs/project-ops/STATUS.md"),
    Path("docs/project-ops/LIVING_CHECKLIST.md"),
    Path("docs/project-ops/CYBERTRACE_V61_DEPLOYMENT_RUNBOOK.md"),
    Path("docs/project-ops/PR83_THESIS_EVIDENCE.md"),
)
MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def test_current_documentation_has_one_canonical_route_per_operator_purpose() -> None:
    index = (REPO_ROOT / "docs/project-ops/README.md").read_text(encoding="utf-8")

    for purpose in (
        "Development setup",
        "Tests",
        "Migrations",
        "Feature enablement",
        "Notifications",
        "Recovery",
        "Break glass",
        "Thesis demo",
    ):
        assert f"| {purpose} |" in index


def test_current_documentation_does_not_repeat_superseded_pr83_truth() -> None:
    combined = "\n".join(
        (REPO_ROOT / path).read_text(encoding="utf-8") for path in CURRENT_DOCS
    )

    assert "20260711_000018" not in combined
    assert "pending secret-bearing payload encryption" not in combined.lower()
    assert "browser execution remains external" not in combined.lower()
    assert "local execution remains blocked" not in combined.lower()


def test_local_markdown_links_in_current_documentation_resolve() -> None:
    broken: list[str] = []
    for relative_source in CURRENT_DOCS:
        source = REPO_ROOT / relative_source
        for target in MARKDOWN_LINK.findall(source.read_text(encoding="utf-8")):
            destination = target.split("#", 1)[0]
            if not destination or "://" in destination or destination.startswith("mailto:"):
                continue
            resolved = (source.parent / destination).resolve()
            if not resolved.exists():
                broken.append(f"{relative_source} -> {target}")

    assert broken == []
