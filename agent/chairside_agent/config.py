from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Mode = Literal["fixtures", "live"]

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parent.parent


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Settings:
    mode: Mode
    record: bool
    xano_base_url: str
    xano_agent_token: str
    perfectcorp_api_key: str
    serpapi_api_key: str
    namecom_username: str
    namecom_token: str
    namecom_base_url: str
    doctavian_base_url: str
    doctavian_api_key: str
    nutrient_api_key: str
    foxit_host: str
    foxit_client_id: str
    foxit_client_secret: str
    llm_provider: str
    gemini_api_key: str
    anthropic_api_key: str
    fixtures_dir: Path
    seed_dir: Path
    state_dir: Path

    @property
    def is_live(self) -> bool:
        return self.mode == "live"

    def require(self, *names: str) -> None:
        """Fail fast: a live adapter needs its credentials before the first call."""
        if not self.is_live:
            return
        missing = [n for n in names if not getattr(self, n)]
        if missing:
            raise ConfigError(f"live mode needs {', '.join(missing)} in the environment")

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        e = os.environ if env is None else env
        mode = e.get("CHAIRSIDE_MODE", "fixtures")
        if mode not in ("fixtures", "live"):
            raise ConfigError(f"CHAIRSIDE_MODE must be fixtures or live, got {mode!r}")
        return cls(
            mode=mode,
            record=e.get("RECORD", "0") == "1",
            xano_base_url=e.get("XANO_BASE_URL", "").rstrip("/"),
            xano_agent_token=e.get("XANO_AGENT_TOKEN", ""),
            perfectcorp_api_key=e.get("PERFECTCORP_API_KEY", ""),
            serpapi_api_key=e.get("SERPAPI_API_KEY", ""),
            namecom_username=e.get("NAMECOM_USERNAME", ""),
            namecom_token=e.get("NAMECOM_TOKEN", ""),
            namecom_base_url=e.get("NAMECOM_BASE_URL", "https://api.dev.name.com").rstrip("/"),
            doctavian_base_url=e.get("DOCTAVIAN_BASE_URL", "").rstrip("/"),
            doctavian_api_key=e.get("DOCTAVIAN_API_KEY", ""),
            nutrient_api_key=e.get("NUTRIENT_API_KEY", ""),
            foxit_host=e.get(
                "FOXIT_CLOUD_API_HOST", "https://na1.fusion.foxit.com/pdf-services"
            ).rstrip("/"),
            foxit_client_id=e.get("FOXIT_CLOUD_API_CLIENT_ID", ""),
            foxit_client_secret=e.get("FOXIT_CLOUD_API_CLIENT_SECRET", ""),
            llm_provider=e.get("LLM_PROVIDER", "gemini"),
            gemini_api_key=e.get("GEMINI_API_KEY", ""),
            anthropic_api_key=e.get("ANTHROPIC_API_KEY", ""),
            fixtures_dir=Path(e.get("CHAIRSIDE_FIXTURES_DIR", PACKAGE_DIR / "fixtures")),
            seed_dir=Path(e.get("CHAIRSIDE_SEED_DIR", REPO_DIR / "seed")),
            state_dir=Path(e.get("CHAIRSIDE_STATE_DIR", REPO_DIR / ".chairside")),
        )
