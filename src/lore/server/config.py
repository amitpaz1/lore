"""Server configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Application settings loaded from environment."""

    database_url: str = ""
    host: str = "0.0.0.0"
    port: int = 8765
    migrations_dir: str = "migrations"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_url=os.environ.get("DATABASE_URL", ""),
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", "8765")),
            migrations_dir=os.environ.get("MIGRATIONS_DIR", "migrations"),
        )


settings = Settings.from_env()
