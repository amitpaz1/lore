"""Server configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Settings:
    """Application settings loaded from environment."""

    database_url: str = ""
    host: str = "0.0.0.0"
    port: int = 8765
    migrations_dir: str = "migrations"

    # OIDC / JWT validation
    oidc_issuer: Optional[str] = None
    oidc_audience: Optional[str] = None
    oidc_role_claim: str = "role"
    oidc_org_claim: str = "tenant_id"

    # Auth mode: "dual" | "oidc-required" | "api-key-only"
    auth_mode: str = "api-key-only"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_url=os.environ.get("DATABASE_URL", ""),
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", "8765")),
            migrations_dir=os.environ.get("MIGRATIONS_DIR", "migrations"),
            oidc_issuer=os.environ.get("OIDC_ISSUER"),
            oidc_audience=os.environ.get("OIDC_AUDIENCE"),
            oidc_role_claim=os.environ.get("OIDC_ROLE_CLAIM", "role"),
            oidc_org_claim=os.environ.get("OIDC_ORG_CLAIM", "tenant_id"),
            auth_mode=os.environ.get("AUTH_MODE", "api-key-only"),
        )


settings = Settings.from_env()
