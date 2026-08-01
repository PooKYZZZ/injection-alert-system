from pathlib import Path


def test_canonical_ml_training_modules_are_importable():
    from ml_model.evaluation import metrics
    from ml_model.preprocessing import dataset_io
    from ml_model.training import confirmatory_runner, losses, model_factory

    assert metrics.evaluate_from_logits is not None
    assert dataset_io.load_data_splits is not None
    assert confirmatory_runner.FinalConfirmatoryRunner is not None
    assert losses.build_loss is not None
    assert model_factory.build_model is not None


def test_canonical_dataset_io_uses_repository_owned_output_root():
    from ml_model.preprocessing import dataset_io

    repository_root = Path(__file__).resolve().parents[2]

    assert dataset_io.REPO_ROOT == repository_root
    assert dataset_io.DEFAULT_RUNS_DIR == (
        repository_root / "ml_model" / "results" / "benchmarks"
    )


def test_canonical_confirmatory_runner_uses_canonical_helper_modules():
    from ml_model.training import confirmatory_runner

    source = Path(confirmatory_runner.__file__).read_text(encoding="utf-8")

    assert "ml_model.preprocessing.dataset_io" in source
    assert "ml_model.training.losses" in source
    assert "ml_model.evaluation.metrics" in source
    assert "ml_model.training.model_factory" in source
    assert "ml_model.notebooks.training" not in source


def test_evaluation_validator_accepts_a_completed_run(tmp_path):
    from ml_model.evaluation.evaluate import validate_run_bundle

    (tmp_path / "run_manifest.json").write_text(
        '{"completed_model_keys": ["distilbert"], "model_keys": ["distilbert"]}',
        encoding="utf-8",
    )
    (tmp_path / "run_status.json").write_text(
        '{"state": "aggregation_completed"}', encoding="utf-8"
    )
    (tmp_path / "run_progress.json").write_text(
        '{"completed_models": 1, "total_models": 1}', encoding="utf-8"
    )
    (tmp_path / "run_failures.json").write_text("[]", encoding="utf-8")

    report = validate_run_bundle(tmp_path)

    assert report["status"] == "complete"
    assert report["completed_models"] == ["distilbert"]
