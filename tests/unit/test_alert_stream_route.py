import asyncio

import pytest
from fastapi.sse import EventSourceResponse

from web_app.application.alert_events import AlertEventBroadcaster
from web_app.presentation.api import routes as routes_module
from web_app.presentation.api.routes import internal_router, stream_alert_events


@pytest.mark.asyncio
async def test_alert_stream_emits_named_minimal_event_and_cleans_up() -> None:
    broadcaster = AlertEventBroadcaster()
    iterator = stream_alert_events(broadcaster=broadcaster)

    pending_event = asyncio.create_task(anext(iterator))
    await asyncio.sleep(0)
    assert broadcaster.subscriber_count == 1

    broadcaster.publish_alert_created()
    event = await asyncio.wait_for(pending_event, timeout=0.1)

    assert event.event == "alert.created"
    assert event.data == {"changed": True}
    await iterator.aclose()
    assert broadcaster.subscriber_count == 0

    route = next(route for route in internal_router.routes if route.path == "/alerts/stream")
    assert route.response_class is EventSourceResponse


@pytest.mark.asyncio
async def test_alert_stream_recycles_after_max_age_and_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(routes_module, "ALERT_STREAM_MAX_AGE_SECONDS", 0.01)
    broadcaster = AlertEventBroadcaster()
    iterator = stream_alert_events(broadcaster=broadcaster)

    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(anext(iterator), timeout=0.1)

    assert broadcaster.subscriber_count == 0
