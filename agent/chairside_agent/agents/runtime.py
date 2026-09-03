"""Wiring: settings → seed → ledger → adapters. Both agents receive one Runtime."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from chairside_agent.config import Settings
from chairside_agent.core.models import ShadeEntry, Sku
from chairside_agent.events import (
    AuditEvent,
    ConsultationEvent,
    EventSink,
    EventWriter,
    LocalLedger,
)

if TYPE_CHECKING:
    from chairside_agent.adapters.doctavian import DoctavianAdapter
    from chairside_agent.adapters.foxit_esign_proxy import EsignProxy
    from chairside_agent.adapters.foxit_pdf import FoxitPdfAdapter
    from chairside_agent.adapters.namecom import NameComAdapter
    from chairside_agent.adapters.nutrient import NutrientAdapter
    from chairside_agent.adapters.serpapi import SerpApiAdapter
    from chairside_agent.adapters.xano import XanoAdapter
    from chairside_agent.adapters.youcam import YouCamAdapter

Printer = Callable[[str], None]


class Seed(BaseModel):
    salon: dict[str, Any]
    skus: list[Sku]
    shade_map: list[ShadeEntry]
    clients: list[dict[str, Any]]
    templates: dict[str, Any]

    def client(self, client_id: str) -> dict[str, Any]:
        for c in self.clients:
            if c["id"] == client_id:
                return c
        raise KeyError(f"unknown client {client_id!r}; see seed/clients.json")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_seed(seed_dir: Path) -> Seed:
    return Seed(
        salon=_read_json(seed_dir / "salon.json"),
        skus=_read_json(seed_dir / "skus.json"),
        shade_map=_read_json(seed_dir / "shade_map.json"),
        clients=_read_json(seed_dir / "clients.json"),
        templates=_read_json(seed_dir / "doctavian_templates.json"),
    )


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _short(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return text if len(text) <= 40 else text[:37] + "..."


def format_event(ev: ConsultationEvent) -> str:
    clock = ev.ts[11:19]
    facts = "  ".join(f"{k}={_short(v)}" for k, v in list(ev.payload.items())[:4])
    return f"{clock}  {ev.type.value:<26}  {facts}"


class LoggingSink:
    """Prints one line per event, then forwards to the real sink."""

    def __init__(self, inner: EventSink, printer: Printer = print) -> None:
        self.inner = inner
        self.printer = printer

    async def append(self, events: list[ConsultationEvent]) -> list[AuditEvent]:
        for ev in events:
            self.printer(format_event(ev))
        return await self.inner.append(events)


class ProjectionStore:
    """Stored projections: what the UI shows. Replay re-folds events and diffs against these."""

    def __init__(self, state_dir: Path) -> None:
        self.dir = state_dir / "projections"
        self.dir.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, projection: dict[str, Any]) -> Path:
        path = self.dir / f"{key}.json"
        path.write_text(json.dumps(projection, indent=2, ensure_ascii=False) + "\n", "utf-8")
        return path

    def load(self, key: str) -> dict[str, Any]:
        path = self.dir / f"{key}.json"
        if not path.exists():
            raise FileNotFoundError(f"no stored projection {key!r} under {self.dir}")
        return _read_json(path)

    def keys(self) -> list[str]:
        return sorted(p.stem for p in self.dir.glob("*.json"))


class RenderCache:
    """Renders are cached by (client_id, sku_code, tool, image_sha256)."""

    def __init__(self, state_dir: Path) -> None:
        self.path = state_dir / "renders.json"
        self._data: dict[str, dict[str, Any]] = _read_json(self.path) if self.path.exists() else {}

    @staticmethod
    def key(client_id: str, sku_code: str | None, tool: str, image_sha256: str) -> str:
        return "|".join([client_id, sku_code or "-", tool, image_sha256])

    def get(self, key: str) -> dict[str, Any] | None:
        return self._data.get(key)

    def put(self, key: str, render: dict[str, Any]) -> None:
        self._data[key] = render
        self.path.write_text(json.dumps(self._data, indent=2) + "\n", "utf-8")


@dataclass(slots=True)
class Runtime:
    settings: Settings
    seed: Seed
    ledger: LocalLedger
    events: EventWriter
    projections: ProjectionStore
    renders: RenderCache
    xano: XanoAdapter
    youcam: YouCamAdapter
    serpapi: SerpApiAdapter
    namecom: NameComAdapter
    nutrient: NutrientAdapter
    foxit_pdf: FoxitPdfAdapter
    esign: EsignProxy
    doctavian: DoctavianAdapter
    closers: list[Callable[[], Any]] = field(default_factory=list)

    @property
    def salon(self) -> dict[str, Any]:
        return self.seed.salon

    async def aclose(self) -> None:
        for adapter in (
            self.xano,
            self.youcam,
            self.serpapi,
            self.namecom,
            self.nutrient,
            self.foxit_pdf,
            self.esign,
            self.doctavian,
        ):
            await adapter.aclose()


def build_runtime(settings: Settings, *, printer: Printer | None = print) -> Runtime:
    from chairside_agent.adapters.doctavian import DoctavianAdapter
    from chairside_agent.adapters.foxit_esign_proxy import EsignProxy
    from chairside_agent.adapters.foxit_pdf import FoxitPdfAdapter
    from chairside_agent.adapters.namecom import NameComAdapter
    from chairside_agent.adapters.nutrient import NutrientAdapter
    from chairside_agent.adapters.serpapi import SerpApiAdapter
    from chairside_agent.adapters.xano import XanoAdapter
    from chairside_agent.adapters.youcam import YouCamAdapter

    seed = load_seed(settings.seed_dir)
    ledger = LocalLedger(settings.state_dir)
    sink: EventSink = LoggingSink(ledger, printer) if printer else ledger
    events = EventWriter(sink, salon_id=seed.salon["id"])
    xano = XanoAdapter(settings, seed.salon["id"], events)
    if settings.is_live:
        events.sink = LoggingSink(xano, printer) if printer else xano
    return Runtime(
        settings=settings,
        seed=seed,
        ledger=ledger,
        events=events,
        projections=ProjectionStore(settings.state_dir),
        renders=RenderCache(settings.state_dir),
        xano=xano,
        youcam=YouCamAdapter(settings, events),
        serpapi=SerpApiAdapter(settings, events),
        namecom=NameComAdapter(settings, events),
        nutrient=NutrientAdapter(settings, events),
        foxit_pdf=FoxitPdfAdapter(settings, events),
        esign=EsignProxy(settings, events),
        doctavian=DoctavianAdapter(settings, events),
    )


def reset_state(settings: Settings) -> None:
    if settings.state_dir.exists():
        shutil.rmtree(settings.state_dir)
