"""Stage-oriented local dashboard pipeline adapters.

The smoke adapter is deliberately honest: it exercises queue/artifact
ordering and marks native training/evaluation evidence ``NOT_RUN``. A native
adapter can be supplied by the controlled laptop operator without changing the
worker or filesystem contracts.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ml_model.retraining.dashboard_contracts import RunState
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    RetrainingRunArtifactRepository,
    RetrainingRunRecord,
)


class PipelineFailure(RuntimeError):
    """Bounded pipeline failure classified by the worker for recovery."""

    def __init__(self, code: str, *, retryable: bool, message: str | None = None):
        self.code = code
        self.retryable = retryable
        self.safe_message = (
            (message or code).replace("\r", " ").replace("\n", " ")[:500]
        )
        super().__init__(self.safe_message)


@dataclass(frozen=True, slots=True)
class PipelineResult:
    terminal_state: RunState
    evidence_status: str


Heartbeat = Callable[[], None]


class SmokeDashboardPipeline:
    """Publish inspectable stage artifacts without native quality claims."""

    def execute(
        self,
        run: RetrainingRunRecord,
        repository: RetrainingRunArtifactRepository,
        heartbeat: Heartbeat,
    ) -> PipelineResult:
        worker_id = run.worker_id
        try:
            heartbeat()
            repository.publish_json_artifact(
                run.run_id,
                "stages/export.json",
                {
                    "stage": "export",
                    "status": "CONTROLLED_SMOKE",
                    "approved_sample_count": run.approved_sample_count,
                    "source_review_count": len(run.source_review_revisions),
                },
                stage="export",
                worker_id=worker_id,
            )
            repository.complete_stage(
                run.run_id,
                next_state=RunState.DATASET_VALIDATED,
                required_artifacts=("stages/export.json",),
                worker_id=worker_id,
                stage="dataset_validated",
            )
            heartbeat()
            repository.publish_json_artifact(
                run.run_id,
                "stages/dataset.json",
                {
                    "stage": "dataset",
                    "status": "CONTROLLED_SMOKE",
                    "dataset_version": f"dashboard-smoke-{run.run_id}",
                    "source_dataset_version": run.source_dataset_version,
                    "preprocessing_version": "NOT_RUN",
                },
                stage="dataset",
                worker_id=worker_id,
            )
            repository.complete_stage(
                run.run_id,
                next_state=RunState.TRAINING,
                required_artifacts=("stages/dataset.json",),
                worker_id=worker_id,
                stage="training",
            )
            heartbeat()
            repository.publish_json_artifact(
                run.run_id,
                "stages/training.json",
                {
                    "stage": "training",
                    "training_status": "NOT_RUN",
                    "model_quality_conclusion": "NOT_PERMITTED",
                },
                stage="training",
                worker_id=worker_id,
            )
            repository.complete_stage(
                run.run_id,
                next_state=RunState.EVALUATING,
                required_artifacts=("stages/training.json",),
                worker_id=worker_id,
                stage="evaluating",
            )
            heartbeat()
            repository.publish_json_artifact(
                run.run_id,
                "stages/evaluation.json",
                {
                    "stage": "evaluation",
                    "evidence_status": "NOT_RUN",
                    "gate_status": "NOT_ENOUGH_EVIDENCE",
                    "native_training_status": "NOT_RUN",
                },
                stage="evaluation",
                worker_id=worker_id,
            )
            repository.publish_json_artifact(
                run.run_id,
                "stages/comparison.json",
                {
                    "stage": "evidence_comparison",
                    "comparison_status": "NOT_RUN",
                    "gate_status": "NOT_ENOUGH_EVIDENCE",
                    "candidate_model_digest": None,
                    "active_model_digest": run.active_model_digest,
                },
                stage="evidence_comparison",
                worker_id=worker_id,
            )
            repository.complete_stage(
                run.run_id,
                next_state=RunState.NOT_ENOUGH_EVIDENCE,
                required_artifacts=(
                    "stages/evaluation.json",
                    "stages/comparison.json",
                ),
                worker_id=worker_id,
                stage="evidence_comparison",
            )
        except PipelineFailure:
            raise
        except Exception as exc:
            raise PipelineFailure(
                "SMOKE_PIPELINE_FAILED",
                retryable=False,
                message=type(exc).__name__,
            ) from exc
        return PipelineResult(
            terminal_state=RunState.NOT_ENOUGH_EVIDENCE,
            evidence_status="NOT_RUN",
        )


class NativeDashboardPipeline:
    """Explicit boundary for native training adapters not run by the smoke path."""

    def execute(
        self,
        run: RetrainingRunRecord,
        repository: RetrainingRunArtifactRepository,
        heartbeat: Heartbeat,
    ) -> PipelineResult:
        del run, repository, heartbeat
        raise PipelineFailure(
            "NATIVE_PIPELINE_REQUIRES_CONTROLLED_ADAPTER",
            retryable=False,
            message="native training is not executed by the default worker",
        )


def run_pipeline_once(
    *,
    repository: RetrainingRunArtifactRepository,
    run_id: str,
    smoke: bool,
) -> PipelineResult:
    run = repository.load_run(run_id)
    if run.state is not RunState.EXPORTING:
        raise PipelineFailure(
            "RUN_NOT_CLAIMED",
            retryable=False,
            message="run must be claimed by a worker before pipeline execution",
        )
    pipeline = SmokeDashboardPipeline() if smoke else NativeDashboardPipeline()
    return pipeline.execute(
        run,
        repository,
        lambda: repository.heartbeat(run_id, worker_id=run.worker_id or ""),
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--smoke", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    repository = RetrainingRunArtifactRepository(args.root)
    try:
        run_pipeline_once(repository=repository, run_id=args.run_id, smoke=args.smoke)
    except PipelineFailure as exc:
        return 20 if exc.retryable else 30
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "NativeDashboardPipeline",
    "PipelineFailure",
    "PipelineResult",
    "SmokeDashboardPipeline",
    "run_pipeline_once",
]
