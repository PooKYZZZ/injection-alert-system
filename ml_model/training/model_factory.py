from __future__ import annotations

from typing import Any, Mapping

import torch
import torch.nn as nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence
from transformers import AutoConfig, AutoModel, AutoModelForSequenceClassification


def build_activation(name: str):
    name = name.lower()
    if name == "gelu":
        return nn.GELU()
    if name == "relu":
        return nn.ReLU()
    raise ValueError(f"Unsupported activation: {name}")


def get_hidden_size(hf_config) -> int:
    for attr in ("hidden_size", "dim", "d_model"):
        if hasattr(hf_config, attr):
            return int(getattr(hf_config, attr))
    raise AttributeError("Could not infer hidden size from model config.")


def infer_head_type(architecture: str) -> str:
    architecture = architecture.lower()
    if architecture == "distilbert_sequence_classification":
        return "hf_sequence_classification_head"
    if architecture == "transformer":
        return "mean_pool_mlp"
    if architecture == "tinybert_bigru_attention":
        return "bigru_attention_mlp"
    if architecture == "albert_cnn":
        return "cnn_mlp"
    return "unknown"


def infer_architecture_family(architecture: str) -> str:
    architecture = architecture.lower()
    if architecture == "distilbert_sequence_classification":
        return "huggingface_sequence_classifier"
    if architecture == "transformer":
        return "backbone_with_standard_head"
    return "architecture_search_variant"


class TransformerClassifier(nn.Module):
    def __init__(
        self,
        model_id: str,
        num_classes: int,
        dropout_prob: float,
        head_hidden_dim: int,
        activation: str,
    ):
        super().__init__()
        self.encoder_config = AutoConfig.from_pretrained(model_id)
        self.encoder = AutoModel.from_pretrained(model_id, config=self.encoder_config)
        hidden_size = get_hidden_size(self.encoder_config)

        self.dropout1 = nn.Dropout(dropout_prob)
        self.classifier_dense = nn.Linear(hidden_size, head_hidden_dim)
        self.activation = build_activation(activation)
        self.layer_norm = nn.LayerNorm(head_hidden_dim)
        self.dropout2 = nn.Dropout(dropout_prob)
        self.output = nn.Linear(head_hidden_dim, num_classes)

    def mean_pool(self, last_hidden_state: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        mask = attention_mask.unsqueeze(-1).type_as(last_hidden_state)
        masked = last_hidden_state * mask
        summed = masked.sum(dim=1)
        denom = mask.sum(dim=1).clamp(min=1e-6)
        return summed / denom

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor):
        encoder_outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        pooled = self.mean_pool(encoder_outputs.last_hidden_state, attention_mask)
        x = self.dropout1(pooled)
        x = self.classifier_dense(x)
        x = self.activation(x)
        x = self.layer_norm(x)
        x = self.dropout2(x)
        logits = self.output(x)
        return {"logits": logits}


class TinyBERTBiGRUAttentionClassifier(nn.Module):
    def __init__(
        self,
        model_id: str,
        num_classes: int,
        dropout_prob: float,
        head_hidden_dim: int,
        rnn_hidden_dim: int,
        rnn_layers: int,
        bidirectional: bool,
        attn_dim: int,
        activation: str,
    ):
        super().__init__()
        self.encoder_config = AutoConfig.from_pretrained(model_id)
        self.encoder = AutoModel.from_pretrained(model_id, config=self.encoder_config)
        encoder_hidden = get_hidden_size(self.encoder_config)

        self.bidirectional = bidirectional
        self.num_directions = 2 if bidirectional else 1
        gru_dropout = 0.0 if rnn_layers == 1 else dropout_prob

        self.gru = nn.GRU(
            input_size=encoder_hidden,
            hidden_size=rnn_hidden_dim,
            num_layers=rnn_layers,
            batch_first=True,
            bidirectional=bidirectional,
            dropout=gru_dropout,
        )
        gru_out_dim = rnn_hidden_dim * self.num_directions

        self.attn_proj = nn.Linear(gru_out_dim, attn_dim)
        self.attn_vector = nn.Linear(attn_dim, 1, bias=False)

        self.dropout1 = nn.Dropout(dropout_prob)
        self.classifier_dense = nn.Linear(gru_out_dim, head_hidden_dim)
        self.activation = build_activation(activation)
        self.layer_norm = nn.LayerNorm(head_hidden_dim)
        self.dropout2 = nn.Dropout(dropout_prob)
        self.output = nn.Linear(head_hidden_dim, num_classes)

    def attention_pool(self, sequence_outputs: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        scores = self.attn_vector(torch.tanh(self.attn_proj(sequence_outputs))).squeeze(-1)
        scores = scores.masked_fill(attention_mask == 0, -1e4)
        weights = torch.softmax(scores, dim=1).unsqueeze(-1)
        return (sequence_outputs * weights).sum(dim=1)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor):
        encoder_outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        lengths = attention_mask.sum(dim=1).clamp(min=1).detach().cpu()
        packed_inputs = pack_padded_sequence(
            encoder_outputs.last_hidden_state,
            lengths,
            batch_first=True,
            enforce_sorted=False,
        )
        packed_outputs, _ = self.gru(packed_inputs)
        sequence_outputs, _ = pad_packed_sequence(
            packed_outputs,
            batch_first=True,
            total_length=encoder_outputs.last_hidden_state.size(1),
        )
        context = self.attention_pool(sequence_outputs, attention_mask)
        x = self.dropout1(context)
        x = self.classifier_dense(x)
        x = self.activation(x)
        x = self.layer_norm(x)
        x = self.dropout2(x)
        logits = self.output(x)
        return {"logits": logits}


class ALBERTCNNClassifier(nn.Module):
    def __init__(
        self,
        model_id: str,
        num_classes: int,
        dropout_prob: float,
        head_hidden_dim: int,
        num_filters: int,
        kernel_sizes,
        activation: str,
    ):
        super().__init__()
        self.encoder_config = AutoConfig.from_pretrained(model_id)
        self.encoder = AutoModel.from_pretrained(model_id, config=self.encoder_config)
        hidden_size = get_hidden_size(self.encoder_config)

        self.convs = nn.ModuleList(
            [
                nn.Conv1d(
                    in_channels=hidden_size,
                    out_channels=num_filters,
                    kernel_size=k,
                    padding=k // 2,
                )
                for k in kernel_sizes
            ]
        )
        # Convolution filters intentionally use a fixed ReLU nonlinearity.
        # The configured activation controls the classification head only.
        self.conv_activation = nn.ReLU()

        self.dropout1 = nn.Dropout(dropout_prob)
        self.classifier_dense = nn.Linear(num_filters * len(kernel_sizes), head_hidden_dim)
        self.activation = build_activation(activation)
        self.layer_norm = nn.LayerNorm(head_hidden_dim)
        self.dropout2 = nn.Dropout(dropout_prob)
        self.output = nn.Linear(head_hidden_dim, num_classes)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor):
        encoder_outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        x = encoder_outputs.last_hidden_state.transpose(1, 2)
        pooled_features = []

        for conv in self.convs:
            feat = self.conv_activation(conv(x))
            pooled = torch.amax(feat, dim=2)
            pooled_features.append(pooled)

        x = torch.cat(pooled_features, dim=1)
        x = self.dropout1(x)
        x = self.classifier_dense(x)
        x = self.activation(x)
        x = self.layer_norm(x)
        x = self.dropout2(x)
        logits = self.output(x)
        return {"logits": logits}


def build_model(cfg: Mapping[str, Any], num_classes: int, device: torch.device) -> nn.Module:
    architecture = cfg["architecture"]
    if architecture == "distilbert_sequence_classification":
        load_kwargs = {"num_labels": num_classes}
        config = None
        if cfg.get("model_revision"):
            config = AutoConfig.from_pretrained(
                cfg["model_id"], revision=cfg["model_revision"]
            )
            load_kwargs["revision"] = cfg["model_revision"]
            load_kwargs["config"] = config
        model = AutoModelForSequenceClassification.from_pretrained(
            cfg["model_id"],
            **load_kwargs,
        )
    elif architecture == "transformer":
        model = TransformerClassifier(
            model_id=cfg["model_id"],
            num_classes=num_classes,
            dropout_prob=cfg["dropout_prob"],
            head_hidden_dim=cfg["head_hidden_dim"],
            activation=cfg.get("activation", "gelu"),
        )
    elif architecture == "tinybert_bigru_attention":
        model = TinyBERTBiGRUAttentionClassifier(
            model_id=cfg["model_id"],
            num_classes=num_classes,
            dropout_prob=cfg["dropout_prob"],
            head_hidden_dim=cfg["head_hidden_dim"],
            rnn_hidden_dim=cfg["rnn_hidden_dim"],
            rnn_layers=cfg["rnn_layers"],
            bidirectional=cfg["bidirectional"],
            attn_dim=cfg["attn_dim"],
            activation=cfg.get("activation", "gelu"),
        )
    elif architecture == "albert_cnn":
        model = ALBERTCNNClassifier(
            model_id=cfg["model_id"],
            num_classes=num_classes,
            dropout_prob=cfg["dropout_prob"],
            head_hidden_dim=cfg["head_hidden_dim"],
            num_filters=cfg["num_filters"],
            kernel_sizes=cfg["kernel_sizes"],
            activation=cfg.get("activation", "gelu"),
        )
    else:
        raise ValueError(f"Unknown architecture: {architecture}")

    return model.to(device)
