from web_app.domain.evidence_relationship import (
    EvidenceRelationship,
    classify_evidence_relationship,
)
from web_app.domain.interfaces import TrafficLogEntity


def _record(**kwargs) -> TrafficLogEntity:
    return TrafficLogEntity(
        transaction_id="producer-transaction",
        http_request="GET /records/search HTTP/1.1",
        **kwargs,
    )


def test_corroborates_class_specific_waf_evidence_for_the_same_attack_class():
    result = classify_evidence_relationship(
        [
            _record(
                prediction="SQL Injection",
                ingest_source="portal_route_bridge",
            ),
            _record(
                prediction="SQL Injection",
                ingest_source="modsec_audit_bridge",
                crs_score=8,
                crs_rule_ids=["942100"],
                matched_rule_tags=["attack-sqli"],
            ),
        ],
        request_correlation_available=True,
    )

    assert result is EvidenceRelationship.CORROBORATED


def test_transaction_id_alone_does_not_count_as_waf_evidence():
    result = classify_evidence_relationship(
        [
            _record(
                prediction="SQL Injection",
                ingest_source="portal_route_bridge",
                crs_score=0,
                crs_rule_ids=["no-crs-match"],
            )
        ],
        request_correlation_available=True,
    )

    assert result is EvidenceRelationship.ML_ONLY


def test_missing_request_correlation_remains_incomplete_for_ml_only_records():
    result = classify_evidence_relationship(
        [_record(prediction="SQL Injection", ingest_source="portal_route_bridge")],
        request_correlation_available=False,
    )

    assert result is EvidenceRelationship.INCOMPLETE


def test_unmapped_crs_evidence_is_incomplete_instead_of_double_counted():
    result = classify_evidence_relationship(
        [
            _record(
                prediction="SQL Injection",
                ingest_source="modsec_audit_bridge",
                crs_score=5,
                crs_rule_ids=["949110"],
                matched_rule_tags=["anomaly-evaluation"],
            )
        ],
        request_correlation_available=False,
    )

    assert result is EvidenceRelationship.INCOMPLETE


def test_class_disagreement_is_reported_explicitly():
    result = classify_evidence_relationship(
        [
            _record(
                prediction="Code Injection",
                ingest_source="portal_route_bridge",
            ),
            _record(
                prediction="SQL Injection",
                ingest_source="modsec_audit_bridge",
                crs_score=8,
                crs_rule_ids=["942100"],
                matched_rule_tags=["attack-sqli"],
            ),
        ],
        request_correlation_available=True,
    )

    assert result is EvidenceRelationship.CONFLICTING
