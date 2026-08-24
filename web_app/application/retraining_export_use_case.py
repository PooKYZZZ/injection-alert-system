"""Application orchestration for immutable approved-review exports."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from ml_model.preprocessing.model_input import MODEL_INPUT_VERSION
from ml_model.retraining.dashboard_contracts import DEFAULT_RETRAINING_RESULTS_ROOT
from ml_model.retraining.dashboard_export import (
    DashboardExportResult,
    ExportLimits,
    export_dashboard_reviews,
)
from web_app.domain.interfaces import (
    ITrafficLabelReviewRepository,
    RetrainingReviewCandidate,
    RetrainingReviewSummary,
)


class RetrainingExportUseCase:
    """Read latest review snapshots and create one bounded local export."""

    def __init__(
        self,
        repository: ITrafficLabelReviewRepository,
        *,
        output_root: Path | str = DEFAULT_RETRAINING_RESULTS_ROOT,
        source_dataset_version: str = "v3_907k_cleaned",
        expected_preprocessing_version: str = MODEL_INPUT_VERSION,
        limits: ExportLimits | None = None,
        max_total_additions: int | None = None,
        max_per_class_additions: int | None = None,
        max_source_fraction: float | None = None,
        source_concentration_min_samples: int | None = None,
        max_repeated_normalized_inputs: int | None = None,
        max_class_distribution_delta: float | None = None,
    ) -> None:
        self._repository = repository
        self._output_root = Path(output_root)
        self._source_dataset_version = source_dataset_version
        self._expected_preprocessing_version = expected_preprocessing_version
        configured_limits = limits or ExportLimits()
        overrides = {
            key: value
            for key, value in {
                "max_total_additions": max_total_additions,
                "max_per_class_additions": max_per_class_additions,
                "max_source_fraction": max_source_fraction,
                "source_concentration_min_samples": source_concentration_min_samples,
                "max_repeated_normalized_inputs": max_repeated_normalized_inputs,
                "max_class_distribution_delta": max_class_distribution_delta,
            }.items()
            if value is not None
        }
        self._limits = replace(configured_limits, **overrides)

    async def execute(
        self,
        *,
        run_id: str,
        limit: int = 10_000,
        candidates: Sequence[RetrainingReviewCandidate] | None = None,
        review_summary: RetrainingReviewSummary | None = None,
    ) -> DashboardExportResult:
        if not 1 <= int(limit) <= 10_000:
            raise ValueError("retraining export limit must be between 1 and 10000")
        summary = review_summary
        selected_candidates = candidates
        if summary is None:
            summary = await self._repository.get_retraining_review_summary()
        if selected_candidates is None:
            selected_candidates = (
                await self._repository.list_latest_retraining_candidates(
                    limit=int(limit)
                )
            )
        return await asyncio.to_thread(
            export_dashboard_reviews,
            selected_candidates,
            run_id=run_id,
            output_root=self._output_root,
            source_dataset_version=self._source_dataset_version,
            expected_preprocessing_version=self._expected_preprocessing_version,
            limits=self._limits,
            review_summary=summary,
        )


__all__ = ["RetrainingExportUseCase"]
