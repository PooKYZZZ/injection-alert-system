from unittest.mock import AsyncMock, MagicMock

import pytest

from web_app.domain.interfaces import TrafficLogPage
from web_app.presentation.api.routes import get_alerts
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
