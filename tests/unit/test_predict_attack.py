from pathlib import Path

import pytest

from ml_model.inference import predict_attack as predict_module


class _FakeModel:
    def __init__(self):
        self.loaded_state = None
        self.strict = None
        self.device = None
        self.in_eval = False

    def load_state_dict(self, state, strict=True):
        self.loaded_state = state
        self.strict = strict

    def to(self, device):
        self.device = device
        return self

    def eval(self):
        self.in_eval = True
        return self


def _write_manifest(run_dir: Path, temperature: float = 0.596868) -> None:
    (run_dir / "serving_manifest.json").write_text(
        (
            "{"
            f"\"temperature\": {temperature}, "
            f"\"run_dir_name\": \"{run_dir.name}\", "
            "\"label_names\": [\"Code Injection\", \"Normal\", \"Other Attacks\", \"SQL Injection\"], "
            "\"max_seq_len\": 128"
            "}"
        ),
        encoding="utf-8",
    )


def test_load_model_prefers_local_run_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    run_dir = tmp_path / "distilbert_v3_907k_cleaned_20260312_133755"
    run_dir.mkdir()
    (run_dir / "config.json").write_text("{}", encoding="utf-8")
    (run_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    _write_manifest(run_dir)

    fake_model = _FakeModel()
    fake_tokenizer = object()

    monkeypatch.setattr(
        predict_module.AutoModelForSequenceClassification,
        "from_pretrained",
        lambda path, local_files_only=False: fake_model,
    )
    monkeypatch.setattr(
        predict_module.AutoTokenizer,
        "from_pretrained",
        lambda path, local_files_only=False: fake_tokenizer,
    )

    model, tokenizer, temperature = predict_module.load_model(
        "distilbert",
        staging_dir=run_dir,
    )

    assert model is fake_model
    assert tokenizer is fake_tokenizer
    assert temperature == pytest.approx(0.596868)
    assert fake_model.device == "cpu"
    assert fake_model.in_eval is True


def test_load_model_requires_serving_manifest_for_primary_path(
    tmp_path: Path,
):
    run_dir = tmp_path / "distilbert_v3_907k_cleaned_20260312_133755"
    run_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="serving manifest"):
        predict_module.load_model("distilbert", staging_dir=run_dir)


def test_load_model_falls_back_to_checkpoint_when_packaged_files_fail_to_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    run_dir = tmp_path / "distilbert_v3_907k_cleaned_20260312_133755"
    run_dir.mkdir()
    (run_dir / "best_distilbert_ckpt.pt").write_bytes(b"checkpoint")
    (run_dir / "config_used.json").write_text(
        '{"model_id": "distilbert-base-uncased"}',
        encoding="utf-8",
    )
    _write_manifest(run_dir)

    fake_model = _FakeModel()
    fake_tokenizer = object()

    def fake_model_loader(source, **kwargs):
        if isinstance(source, Path):
            raise OSError("local artifact incomplete")
        return fake_model

    def fake_tokenizer_loader(source, **kwargs):
        if isinstance(source, Path):
            raise OSError("local tokenizer incomplete")
        return fake_tokenizer

    monkeypatch.setattr(
        predict_module.AutoModelForSequenceClassification,
        "from_pretrained",
        fake_model_loader,
    )
    monkeypatch.setattr(
        predict_module.AutoTokenizer,
        "from_pretrained",
        fake_tokenizer_loader,
    )
    monkeypatch.setattr(
        predict_module.torch,
        "load",
        lambda path, map_location="cpu", weights_only=True: {"weights": 1},
    )

    model, tokenizer, temperature = predict_module.load_model(
        "distilbert",
        staging_dir=run_dir,
    )

    assert model is fake_model
    assert tokenizer is fake_tokenizer
    assert temperature == pytest.approx(0.596868)
    assert fake_model.loaded_state == {"weights": 1}
    assert fake_model.strict is True
    assert "Falling back to legacy checkpoint-based loading" in caplog.text
