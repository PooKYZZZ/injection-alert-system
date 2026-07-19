import asyncio

import pytest

from web_app.application.alert_events import AlertEventBroadcaster


@pytest.mark.asyncio
async def test_publish_reaches_every_active_subscriber() -> None:
    broadcaster = AlertEventBroadcaster()

    async with broadcaster.subscribe() as first, broadcaster.subscribe() as second:
        broadcaster.publish_alert_created()

        assert await asyncio.wait_for(first.get(), timeout=0.1) == {"changed": True}
        assert await asyncio.wait_for(second.get(), timeout=0.1) == {"changed": True}


@pytest.mark.asyncio
async def test_full_subscriber_queue_coalesces_without_blocking() -> None:
    broadcaster = AlertEventBroadcaster()

    async with broadcaster.subscribe() as events:
        broadcaster.publish_alert_created()
        broadcaster.publish_alert_created()

        assert events.qsize() == 1
        assert await asyncio.wait_for(events.get(), timeout=0.1) == {"changed": True}


@pytest.mark.asyncio
async def test_subscriber_is_removed_when_context_closes() -> None:
    broadcaster = AlertEventBroadcaster()

    async with broadcaster.subscribe():
        assert broadcaster.subscriber_count == 1

    assert broadcaster.subscriber_count == 0
