"""Application configuration via environment variables."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """GoalMind backend settings loaded from environment."""

    # API-Football
    api_football_key: str = ""
    api_football_base_url: str = "https://v3.football.api-sports.io"

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Upstash Redis (accepts both UPSTASH_REDIS_* and UPSTASH_REDIS_REST_* from dashboard)
    upstash_redis_url: str = Field(
        default="",
        validation_alias=AliasChoices("UPSTASH_REDIS_URL", "UPSTASH_REDIS_REST_URL"),
    )
    upstash_redis_token: str = Field(
        default="",
        validation_alias=AliasChoices("UPSTASH_REDIS_TOKEN", "UPSTASH_REDIS_REST_TOKEN"),
    )

    # App
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"
    next_public_frontend_url: str = "http://localhost:3000"
    admin_api_key: str = ""
    trusted_hosts: str = ""
    trust_proxy_headers: bool = False

    # Data source: hybrid (recommended), statsbomb, or api_football
    data_source: str = "hybrid"

    # API-Football (paid / limited free tier)
    wc_league_id: int = 1
    wc_season: int = 2022

    # StatsBomb open data — historical World Cups (free, GitHub)
    statsbomb_competition_id: int = 43  # FIFA World Cup
    statsbomb_season_ids: str = "106,3"  # 2022, 2018

    # OpenFootball — WC 2026 schedule (free, public domain)
    openfootball_wc_year: int = 2026

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @property
    def api_football_configured(self) -> bool:
        return bool(self.api_football_key.strip())

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url.strip() and self.supabase_key.strip())

    @property
    def redis_configured(self) -> bool:
        url = self.upstash_redis_url.strip()
        token = self.upstash_redis_token.strip()
        if not url or not token:
            return False
        combined = f"{url} {token}".lower()
        placeholders = ("your-redis", "your_upstash", "example.com")
        return not any(marker in combined for marker in placeholders)

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def rate_limit_fail_closed(self) -> bool:
        return self.is_production

    @property
    def allowed_cors_origins(self) -> list[str]:
        origins: list[str] = []
        for raw in (self.next_public_frontend_url, self.cors_origins):
            for part in raw.split(","):
                origin = part.strip()
                if origin and origin not in origins:
                    origins.append(origin)
        return origins

    @property
    def trusted_hosts_list(self) -> list[str]:
        if not self.trusted_hosts.strip():
            return []
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]

    @property
    def statsbomb_season_id_list(self) -> list[int]:
        return [int(s.strip()) for s in self.statsbomb_season_ids.split(",") if s.strip()]

    @property
    def use_statsbomb(self) -> bool:
        return self.data_source in {"hybrid", "statsbomb"}

    @property
    def use_openfootball(self) -> bool:
        return self.data_source in {"hybrid", "openfootball"}

    @property
    def use_api_football(self) -> bool:
        return self.data_source == "api_football"


settings = Settings()
