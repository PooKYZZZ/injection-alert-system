"""In-process alert-change publication for the single-process thesis runtime."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Protocol


AlertChangedSignal = dict[str, bool]


class IAlertEventPublisher(Protocol):
    """Narrow application seam used after a visible alert is persisted."""

    def publish_alert_created(self) -> None:
        """Notify current subscribers without waiting for network consumers."""
        ...


class AlertEventBroadcaster:
    """Fan out coalesced alert-change signals to bounded subscriber queues."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[AlertChangedSignal]] = set()

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[AlertChangedSignal]]:
        queue: asyncio.Queue[AlertChangedSignal] = asyncio.Queue(maxsize=1)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)

    def publish_alert_created(self) -> None:
        for queue in tuple(self._subscribers):
            try:
                queue.put_nowait({"changed": True})
            except asyncio.QueueFull:
                # The unread signal already tells this subscriber to refetch.
                continue
