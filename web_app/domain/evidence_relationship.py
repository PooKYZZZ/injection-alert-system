"""Deterministic categorical relationship between ML and CRS evidence."""

from __future__ import annotations

from enum import StrEnum
from collections.abc import Sequence

from web_app.domain.classification_scope import ACTIONABLE_ATTACK_CLASSES
from web_app.domain.enforcement import evidence_from_waf_fields
from web_app.domain.interfaces import TrafficLogEntity


class EvidenceRelationship(StrEnum):
    CORROBORATED = "CORROBORATED"
    ML_ONLY = "ML_ONLY"
    WAF_ONLY = "WAF_ONLY"
    CONFLICTING = "CONFLICTING"
    INCOMPLETE = "INCOMPLETE"


_NON_EVIDENCE_RULE_IDS = {"", "no-crs-match", "unknown-rule"}


def classify_evidence_relationship(
    records: Sequence[TrafficLogEntity], *, request_correlation_available: bool
) -> EvidenceRelationship:
    """Classify available evidence without inventing a confidence score.

    A ModSecurity record contains both its CRS evidence and the inference made
    from that same transaction, so that single record is directly related even
    when its separate request-correlation header was unavailable. Other
    producer records require the trusted request ID to connect evidence.
    """

    if not records:
        return EvidenceRelationship.INCOMPLETE

    has_same_record_waf_evidence = any(
        record.ingest_source == "modsec_audit_bridge" for record in records
    )
    if not request_correlation_available and not has_same_record_waf_evidence:
        return EvidenceRelationship.INCOMPLETE

    ml_classes = {
        record.prediction
        for record in records
        if record.prediction in ACTIONABLE_ATTACK_CLASSES
    }
    waf_classes: set[str] = set()
    has_waf_evidence = False

    for record in records:
        if record.ingest_source != "modsec_audit_bridge":
            continue
        rule_ids = tuple(
            rule_id
            for rule_id in (record.crs_rule_ids or [])
            if rule_id.strip().lower() not in _NON_EVIDENCE_RULE_IDS
        )
        tags = tuple(tag for tag in (record.matched_rule_tags or []) if tag.strip())
        has_waf_evidence = has_waf_evidence or bool(
            (record.crs_score is not None and record.crs_score > 0)
            or rule_ids
            or tags
        )
        evidence = evidence_from_waf_fields(
            source_verification_status=record.source_verification_status,
            crs_score=record.crs_score,
            crs_rule_ids=list(rule_ids),
            matched_rule_tags=list(tags),
        )
        waf_classes.update(
            attack_class
            for attack_class in ACTIONABLE_ATTACK_CLASSES
            if evidence.strongly_supports(attack_class)
        )

    if ml_classes and waf_classes:
        if len(ml_classes) == len(waf_classes) == 1 and ml_classes == waf_classes:
            return EvidenceRelationship.CORROBORATED
        return EvidenceRelationship.CONFLICTING
    if ml_classes:
        return (
            EvidenceRelationship.INCOMPLETE
            if has_waf_evidence
            else EvidenceRelationship.ML_ONLY
        )
    if waf_classes:
        return EvidenceRelationship.WAF_ONLY
    return EvidenceRelationship.INCOMPLETE
