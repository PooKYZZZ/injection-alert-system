from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch


def test_distilbert_registry_selects_native_sequence_classifier():
    from ml_model.training.train import DEFAULT_MODEL_REGISTRY

    config = DEFAULT_MODEL_REGISTRY["distilbert"]

    assert config["architecture"] == "distilbert_sequence_classification"
    assert config.get("head_hidden_dim") in (None,)


def test_native_distilbert_build_uses_hugging_face_sequence_classifier(monkeypatch):
    from ml_model.training import model_factory

    calls: list[tuple[str, int]] = []

    class FakeNativeModel(torch.nn.Module):
        def forward(self, input_ids, attention_mask):
            return {"logits": torch.zeros((input_ids.shape[0], 4))}

    def fake_from_pretrained(model_id: str, *, config, revision):
        calls.append((model_id, config.num_labels))
        return FakeNativeModel()

    monkeypatch.setattr(
        model_factory,
        "AutoModelForSequenceClassification",
        SimpleNamespace(from_pretrained=fake_from_pretrained),
        raising=False,
    )
    monkeypatch.setattr(
        model_factory,
        "AutoConfig",
        SimpleNamespace(
            from_pretrained=lambda model_id, *, revision: SimpleNamespace(
                revision=revision, num_labels=2
            )
        ),
    )

    model = model_factory.build_model(
        {
            "architecture": "distilbert_sequence_classification",
            "model_id": "distilbert-base-uncased",
            "model_revision": "verified-revision",
        },
        num_classes=4,
        device=torch.device("cpu"),
    )

    assert calls == [("distilbert-base-uncased", 4)]
    outputs = model(
        input_ids=torch.ones((2, 3), dtype=torch.long),
        attention_mask=torch.ones((2, 3), dtype=torch.long),
    )
    assert outputs["logits"].shape == (2, 4)
    assert all(
        not any(part in key for part in ("classifier_dense", "layer_norm", "output"))
        for key in model.state_dict()
    )


def test_unresolved_or_missing_model_revision_is_rejected(monkeypatch):
    from ml_model.training import model_factory

    def unexpected_loader(*args, **kwargs):
        raise AssertionError("model loader must not receive an unresolved revision")

    monkeypatch.setattr(
        model_factory,
        "AutoConfig",
        SimpleNamespace(from_pretrained=unexpected_loader),
    )

    for revision in (None, "unresolved"):
        config = {
            "architecture": "distilbert_sequence_classification",
            "model_id": "distilbert-base-uncased",
        }
        if revision is not None:
            config["model_revision"] = revision
        with pytest.raises(ValueError, match="pinned model_revision"):
            model_factory.build_model(config, 4, torch.device("cpu"))


def test_native_distilbert_build_passes_pinned_revision(monkeypatch):
    from ml_model.training import model_factory

    calls: list[dict[str, object]] = []

    class FakeNativeModel(torch.nn.Module):
        pass

    def fake_from_pretrained(model_id: str, *, revision: str, config):
        calls.append(
            {
                "model_id": model_id,
                "num_labels": config.num_labels,
                "revision": revision,
            }
        )
        return FakeNativeModel()

    monkeypatch.setattr(
        model_factory,
        "AutoModelForSequenceClassification",
        SimpleNamespace(from_pretrained=fake_from_pretrained),
        raising=False,
    )
    monkeypatch.setattr(
        model_factory,
        "AutoConfig",
        SimpleNamespace(
            from_pretrained=lambda model_id, *, revision: SimpleNamespace(
                revision=revision, num_labels=2
            )
        ),
    )

    model_factory.build_model(
        {
            "architecture": "distilbert_sequence_classification",
            "model_id": "distilbert-base-uncased",
            "model_revision": "verified-revision",
        },
        num_classes=4,
        device=torch.device("cpu"),
    )

    assert calls == [
        {
            "model_id": "distilbert-base-uncased",
            "num_labels": 4,
            "revision": "verified-revision",
        }
    ]


def test_native_distilbert_metadata_is_truthful():
    from ml_model.training.model_factory import (
        infer_architecture_family,
        infer_head_type,
    )

    assert infer_head_type("distilbert_sequence_classification") == (
        "hf_sequence_classification_head"
    )
    assert infer_architecture_family("distilbert_sequence_classification") == (
        "huggingface_sequence_classifier"
    )


def test_legacy_transformer_architecture_is_still_explicitly_selectable(monkeypatch):
    from ml_model.training import model_factory

    class FakeEncoder(torch.nn.Module):
        def forward(self, input_ids, attention_mask):
            return SimpleNamespace(last_hidden_state=torch.zeros((2, 3, 4)))

    monkeypatch.setattr(
        model_factory,
        "AutoConfig",
        SimpleNamespace(
            from_pretrained=lambda model_id, *, revision: SimpleNamespace(
                hidden_size=4, revision=revision
            )
        ),
    )
    monkeypatch.setattr(
        model_factory,
        "AutoModel",
        SimpleNamespace(
            from_pretrained=lambda model_id, *, config, revision: FakeEncoder()
        ),
    )

    model = model_factory.build_model(
        {
            "architecture": "transformer",
            "model_id": "historical/model",
            "model_revision": "historical-pinned-revision",
            "dropout_prob": 0.1,
            "head_hidden_dim": 8,
            "activation": "gelu",
        },
        num_classes=4,
        device=torch.device("cpu"),
    )

    assert isinstance(model, model_factory.TransformerClassifier)
    assert model_factory.infer_head_type("transformer") == "mean_pool_mlp"
    assert model_factory.infer_architecture_family("transformer") == (
        "backbone_with_standard_head"
    )
