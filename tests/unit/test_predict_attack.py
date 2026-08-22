import json
from pathlib import Path
from types import SimpleNamespace

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


class _FakeInferenceModel:
    def __init__(self, logits=None):
        self.logits = predict_module.torch.tensor(
            [[0.0, 0.0, 0.0, 0.0] if logits is None else logits]
        )

    def __call__(self, **encoded):
        return SimpleNamespace(logits=self.logits)


def _fake_tokenizer(*args, **kwargs):
    return {
        "input_ids": predict_module.torch.zeros(
            (1, 1),
            dtype=predict_module.torch.long,
        )
    }


def _write_manifest(
    run_dir: Path,
    *,
    temperature=1.0,
    label_names=None,
    max_seq_len=None,
) -> None:
    data = {
        "temperature": temperature,
        "label_names": predict_module.LABEL_NAMES if label_names is None else label_names,
        "max_seq_len": predict_module.MAX_SEQ_LEN if max_seq_len is None else max_seq_len,
    }
    (run_dir / predict_module.MANIFEST_NAME).write_text(
        json.dumps(data, indent=2),
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
    assert temperature == 1.0
    assert fake_model.device == "cpu"
    assert fake_model.in_eval is True


def test_load_model_accepts_a_direct_packaged_candidate_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    candidate_dir = tmp_path / "candidate_model"
    candidate_dir.mkdir()
    (candidate_dir / "config.json").write_text("{}", encoding="utf-8")
    (candidate_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    _write_manifest(candidate_dir, temperature=0.91)

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
        staging_dir=candidate_dir,
    )

    assert model is fake_model
    assert tokenizer is fake_tokenizer
    assert temperature == 0.91


def test_load_model_uses_packaged_manifest_temperature(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    run_dir = tmp_path / "distilbert_v3_907k_cleaned_20260312_133755"
    run_dir.mkdir()
    (run_dir / "config.json").write_text("{}", encoding="utf-8")
    (run_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    _write_manifest(run_dir, temperature=0.77)

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
    assert temperature == 0.77


@pytest.mark.parametrize(
    ("manifest_kwargs", "message_fragment"),
    [
        ({"temperature": "not-a-float"}, "missing or invalid field 'temperature'"),
        ({"label_names": "SQL Injection"}, "missing or invalid field 'label_names'"),
        ({"label_names": ["SQL Injection"]}, "'label_names' mismatch"),
        ({"max_seq_len": "128"}, "missing or invalid field 'max_seq_len'"),
        ({"max_seq_len": 64}, "'max_seq_len' mismatch"),
    ],
)
def test_load_model_rejects_invalid_packaged_manifest(
    tmp_path: Path,
    manifest_kwargs: dict[str, object],
    message_fragment: str,
):
    run_dir = tmp_path / "distilbert_v3_907k_cleaned_20260312_133755"
    run_dir.mkdir()
    _write_manifest(run_dir, **manifest_kwargs)

    with pytest.raises(RuntimeError, match=message_fragment):
        predict_module.load_model("distilbert", staging_dir=run_dir)


def test_load_model_falls_back_to_checkpoint_when_local_files_missing(
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

    fake_model = _FakeModel()
    fake_tokenizer = object()
    calls = {"model": [], "tokenizer": []}

    def fake_model_loader(source, **kwargs):
        calls["model"].append((source, kwargs))
        if isinstance(source, Path):
            raise OSError("local artifact incomplete")
        return fake_model

    def fake_tokenizer_loader(source, **kwargs):
        calls["tokenizer"].append((source, kwargs))
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
    assert temperature == 1.0
    assert fake_model.loaded_state == {"weights": 1}
    assert fake_model.strict is True
    assert calls["model"][1] == (
        "distilbert-base-uncased",
        {"num_labels": predict_module.NUM_CLASSES, "local_files_only": True},
    )
    assert calls["tokenizer"][0] == (
        "distilbert-base-uncased",
        {"local_files_only": True},
    )
    assert "Falling back to checkpoint-based loading" in caplog.text


def test_predict_attack_builds_payload_from_model_logits():
    result = predict_module.predict_attack(
        "SELECT * FROM users",
        _FakeInferenceModel(logits=[0.0, 0.0, 0.0, 10.0]),
        _fake_tokenizer,
        return_latency=False,
    )

    assert result["label"] == predict_module.LABEL_NAMES[3]
    assert result["label_idx"] == 3
    assert result["max_prob"] == pytest.approx(0.999864)
    assert result["tier"] == "CRITICAL"
    assert sum(result["probs"]) == pytest.approx(1.0, abs=2e-6)


@pytest.mark.parametrize(
    ("max_probability", "expected_tier"),
    [
        (0.80, "MEDIUM"),
        (0.90, "CRITICAL"),
    ],
)
def test_predict_attack_classifies_confidence_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    max_probability: float,
    expected_tier: str,
):
    remaining_probability = (1.0 - max_probability) / 3
    probabilities = predict_module.torch.tensor(
        [
            max_probability,
            remaining_probability,
            remaining_probability,
            remaining_probability,
        ],
        dtype=predict_module.torch.float64,
    )
    monkeypatch.setattr(
        predict_module.torch,
        "softmax",
        lambda logits, dim: probabilities,
    )

    result = predict_module.predict_attack(
        "SELECT * FROM users",
        _FakeInferenceModel(),
        _fake_tokenizer,
        return_latency=False,
    )

    assert result["max_prob"] == max_probability
    assert result["tier"] == expected_tier
