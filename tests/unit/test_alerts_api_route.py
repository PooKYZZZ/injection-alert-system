from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from web_app.domain.interfaces import TrafficLogEntity, TrafficLogPage
from web_app.presentation.api.routes import get_alert_by_id, get_alerts
from web_app.presentation.schemas.schemas import AlertQueryParams


@pytest.mark.asyncio
async def test_alerts_route_forwards_opt_in_scope_to_repository() -> None:
    repository = MagicMock()
    repository.get_alert_list = AsyncMock(
        return_value=TrafficLogPage(items=[], total=0, page=1, page_size=20)
    )

    response = await get_alerts(
        query=AlertQueryParams(include_normal=True),
        repository=repository,
    )

    assert response.total == 0
    repository.get_alert_list.assert_awaited_once()
    assert repository.get_alert_list.await_args.kwargs["include_normal"] is True


@pytest.mark.asyncio
async def test_alerts_list_does_not_serialize_persisted_query_string() -> None:
    entity = TrafficLogEntity(
        id=17,
        timestamp=datetime(2026, 9, 25, tzinfo=timezone.utc),
        request_method="GET",
        request_path="/records/search",
        query_string="query=synthetic%20test",
        http_request="GET /records/search HTTP/1.1",
        prediction="Code Injection",
        confidence=0.71,
        confidence_level="MEDIUM",
    )
    repository = MagicMock()
    repository.get_alert_list = AsyncMock(
        return_value=TrafficLogPage(items=[entity], total=1, page=1, page_size=20)
    )

    response = await get_alerts(
        query=AlertQueryParams(),
        repository=repository,
    )

    serialized = response.model_dump(mode="json")
    assert serialized["items"][0]["payload_snippet"] == "GET /records/search HTTP/1.1"
    assert "query_string" not in serialized["items"][0]


@pytest.mark.asyncio
async def test_alert_detail_returns_the_persisted_redacted_query_string() -> None:
    entity = TrafficLogEntity(
        id=18,
        timestamp=datetime(2026, 9, 25, tzinfo=timezone.utc),
        request_method="GET",
        request_path="/records/search",
        query_string="query=synthetic%20lookup&token=%5BREDACTED%5D",
        http_request="GET /records/search HTTP/1.1",
        prediction="Code Injection",
        confidence=0.71,
        confidence_level="MEDIUM",
    )
    repository = MagicMock()
    repository.get_operational_alert_by_id = AsyncMock(return_value=entity)

    response = await get_alert_by_id(alert_id=18, repository=repository)

    assert response.query_string == "query=synthetic%20lookup&token=%5BREDACTED%5D"
    repository.get_operational_alert_by_id.assert_awaited_once_with(18)
