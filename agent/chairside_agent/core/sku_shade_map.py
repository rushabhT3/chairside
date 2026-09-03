from __future__ import annotations

from chairside_agent.core.models import ShadeEntry, Sku


class UnknownShadeError(KeyError):
    def __init__(self, shade_code: str | None) -> None:
        super().__init__(shade_code)
        self.shade_code = shade_code

    def __str__(self) -> str:
        return f"shade code {self.shade_code!r} is not in the salon's shade map"


def sku_shade_map(shade_code: str, shade_map: list[ShadeEntry]) -> ShadeEntry:
    for entry in shade_map:
        if entry.code == shade_code:
            return entry
    raise UnknownShadeError(shade_code)


def shade_for_sku(sku: Sku, shade_map: list[ShadeEntry]) -> ShadeEntry:
    if sku.shade_code is None:
        raise UnknownShadeError(None)
    return sku_shade_map(sku.shade_code, shade_map)
