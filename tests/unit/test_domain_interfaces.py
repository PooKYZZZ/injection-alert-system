from web_app.domain.interfaces import TrafficLogEntity
from web_app.domain.source_address import SourceProvenance, SourceVerificationStatus


def test_traffic_log_domain_defaults_are_conservative() -> None:
    entity = TrafficLogEntity()

    assert entity.source_provenance is SourceProvenance.DIRECT_REMOTE_ADDR
    assert entity.source_verification_status is SourceVerificationStatus.UNVERIFIED
    assert entity.source_verification_status is not SourceVerificationStatus.VERIFIED
