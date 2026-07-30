from datetime import datetime, timedelta, timezone

import pytest

from web_app.application.post_triage_enforcement import (
    PostTriageEnforcementCoordinator,
    WafMutationOutcome,
)
from web_app.domain.enforcement import EnforcementMode


class RecordingGenericRecommendation:
    def __init__(self, recorded: bool = True):
        self.recorded = recorded
        self.calls: list[dict[str, object]] = []

    async def execute(self, **kwargs):
        self.calls.append(kwargs)
        return self.recorded


class RecordingWafStateMutation:
    def __init__(self, outcome: WafMutationOutcome):
        self.outcome = outcome
        self.calls: list[dict[str, object]] = []

    async def record_critical_waf_recommendation(self, **kwargs):
        self.calls.append(kwargs)
        return self.outcome


@pytest.mark.asyncio
async def test_critical_pr7_candidate_uses_only_the_atomic_waf_writer():
    generic = RecordingGenericRecommendation()
    waf = RecordingWafStateMutation(
        WafMutationOutcome(
            category="ACTIVATED",
            recommendation_id=17,
            revision=4,
            state_changed=True,
        )
    )
    occurred_at = datetime(2026, 7, 30, 10, tzinfo=timezone.utc)
    coordinator = PostTriageEnforcementCoordinator(
        generic_use_case=generic,
        waf_repository=waf,
        enforcement_mode=EnforcementMode.ENFORCE,
        pr7_mutation_enabled=True,
        recommendation_ttl_seconds=900,
        clock=lambda: occurred_at,
    )

    result = await coordinator.execute(
        alert_id=42,
        prediction="SQL Injection",
        confidence_level="CRITICAL",
        request_path="/records/search",
        occurred_at=occurred_at,
    )

    assert result.route == "PR7"
    assert result.category == "ACTIVATED"
    assert result.recorded is True
    assert result.recommendation_id == 17
    assert result.revision == 4
    assert result.state_changed is True
    assert generic.calls == []
    assert waf.calls == [
        {
            "trigger_traffic_log_id": 42,
            "recommendation_expires_at": occurred_at + timedelta(seconds=900),
            "effective_expires_at": occurred_at + timedelta(seconds=900),
            "capacity": 64,
        }
    ]


@pytest.mark.asyncio
async def test_non_critical_result_keeps_generic_recommendation_ownership():
    generic = RecordingGenericRecommendation()
    waf = RecordingWafStateMutation(
        WafMutationOutcome("INELIGIBLE", 0, 3, False)
    )
    coordinator = PostTriageEnforcementCoordinator(
        generic_use_case=generic,
        waf_repository=waf,
        enforcement_mode=EnforcementMode.ENFORCE,
        pr7_mutation_enabled=True,
        recommendation_ttl_seconds=900,
    )

    result = await coordinator.execute(
        alert_id=42,
        prediction="SQL Injection",
        confidence_level="HIGH",
        request_path="/records/search",
        occurred_at=None,
    )

    assert result.route == "GENERIC"
    assert result.category == "RECORDED"
    assert result.recorded is True
    assert len(generic.calls) == 1
    assert waf.calls == []


@pytest.mark.asyncio
async def test_disabled_pr7_gate_does_not_mutate_waf_state():
    generic = RecordingGenericRecommendation(recorded=False)
    waf = RecordingWafStateMutation(
        WafMutationOutcome("ACTIVATED", 17, 4, True)
    )
    coordinator = PostTriageEnforcementCoordinator(
        generic_use_case=generic,
        waf_repository=waf,
        enforcement_mode=EnforcementMode.ENFORCE,
        pr7_mutation_enabled=False,
        recommendation_ttl_seconds=900,
    )

    result = await coordinator.execute(
        alert_id=42,
        prediction="SQL Injection",
        confidence_level="CRITICAL",
        request_path="/records/search",
        occurred_at=None,
    )

    assert result.route == "GENERIC"
    assert result.category == "NO_CHANGE"
    assert result.recorded is False
    assert waf.calls == []


@pytest.mark.asyncio
async def test_missing_alert_id_is_not_recorded():
    generic = RecordingGenericRecommendation()
    waf = RecordingWafStateMutation(
        WafMutationOutcome("ACTIVATED", 17, 4, True)
    )
    coordinator = PostTriageEnforcementCoordinator(
        generic_use_case=generic,
        waf_repository=waf,
        enforcement_mode=EnforcementMode.ENFORCE,
        pr7_mutation_enabled=True,
        recommendation_ttl_seconds=900,
    )

    result = await coordinator.execute(
        alert_id=None,
        prediction="SQL Injection",
        confidence_level="CRITICAL",
        request_path="/records/search",
        occurred_at=None,
    )

    assert result.route == "NONE"
    assert result.category == "NOT_APPLICABLE"
    assert result.recorded is False
    assert generic.calls == []
    assert waf.calls == []


@pytest.mark.asyncio
async def test_pr7_candidate_normalizes_naive_persisted_event_time_as_utc():
    waf = RecordingWafStateMutation(
        WafMutationOutcome("ACTIVATED", 17, 4, True)
    )
    coordinator = PostTriageEnforcementCoordinator(
        generic_use_case=RecordingGenericRecommendation(),
        waf_repository=waf,
        enforcement_mode=EnforcementMode.ENFORCE,
        pr7_mutation_enabled=True,
        recommendation_ttl_seconds=900,
    )

    await coordinator.execute(
        alert_id=42,
        prediction="SQL Injection",
        confidence_level="CRITICAL",
        request_path="/records/search",
        occurred_at=datetime(2026, 7, 30, 10),
    )

    assert waf.calls[0]["recommendation_expires_at"] == datetime(
        2026, 7, 30, 10, 15, tzinfo=timezone.utc
    )
