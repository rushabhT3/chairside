from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import httpx

from chairside_agent import fixtures
from chairside_agent.config import Settings
from chairside_agent.events import EventType, EventWriter
from chairside_agent.hashing import sha256_hex

LiveCall = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class VendorAdapter:
    """Shared live/fixtures switch. Subclasses set `vendor` and `server`."""

    vendor: str = ""
    server: str = ""

    def __init__(
        self,
        settings: Settings,
        events: EventWriter,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self.events = events
        self.http = http or httpx.AsyncClient(timeout=httpx.Timeout(60.0))

    async def aclose(self) -> None:
        await self.http.aclose()

    async def call(
        self,
        primitive: str,
        request: dict[str, Any],
        live: LiveCall,
        *,
        variant: str = "default",
        units: int = 1,
        tool: str | None = None,
        server: str | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        if self.settings.is_live:
            response = await live(request)
            latency_ms = int((time.perf_counter() - started) * 1000)
            if self.settings.record:
                fixtures.save(
                    self.settings.fixtures_dir,
                    fixtures.Cassette(
                        vendor=self.vendor,
                        primitive=primitive,
                        variant=variant,
                        recorded_at=datetime.now(UTC).isoformat(timespec="seconds"),
                        request=request,
                        response=response,
                        units=units,
                        latency_ms=latency_ms,
                    ),
                )
        else:
            cassette = fixtures.load(self.settings.fixtures_dir, self.vendor, primitive, variant)
            response = cassette.response
            latency_ms = cassette.latency_ms
            units = cassette.units
        await self.events.emit(
            EventType.TOOL_CALLED,
            {
                "tool": tool or primitive,
                "server": server or self.server,
                "latency_ms": latency_ms,
                "units": units,
                "result_sha256": sha256_hex(
                    json.dumps(response, sort_keys=True, ensure_ascii=False)
                ),
                "as_of": datetime.now(UTC).isoformat(timespec="seconds"),
            },
        )
        return response
