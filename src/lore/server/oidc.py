"""OIDC JWT validation for Lore server.

Lore is a headless API — it only validates pre-minted JWTs from an IdP.
Uses JWKS auto-discovery with caching and cache-bust-on-miss (QA: F2).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

try:
    import jwt
    from jwt import PyJWKClient, PyJWKClientError
except ImportError:
    raise ImportError("PyJWT[crypto] is required. Install with: pip install 'PyJWT[crypto]>=2.8'")

logger = logging.getLogger(__name__)


@dataclass
class OidcIdentity:
    """Resolved OIDC user identity from a validated JWT."""

    sub: str
    email: Optional[str]
    name: Optional[str]
    org_id: Optional[str]
    role: str


class OidcValidator:
    """Validates OIDC JWTs against the IdP's JWKS endpoint.

    Features:
    - JWKS key caching with 1-hour TTL
    - Cache-bust-on-miss: if a kid is not found, force re-fetch (max once/min)
    - Restricted algorithms: RS256, RS384, RS512
    - Graceful IdP unreachability: fail-open with logging (QA: F1)
    """

    ALLOWED_ALGORITHMS = ["RS256", "RS384", "RS512"]
    # Minimum interval between forced JWKS re-fetches (seconds)
    _MIN_REFETCH_INTERVAL = 60.0

    def __init__(
        self,
        issuer: str,
        audience: Optional[str] = None,
        role_claim: str = "role",
        org_claim: str = "tenant_id",
    ):
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self.role_claim = role_claim
        self.org_claim = org_claim
        jwks_url = f"{self.issuer}/.well-known/jwks.json"
        self._jwk_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
        self._last_force_fetch: float = 0.0

    def validate(self, token: str) -> Optional[OidcIdentity]:
        """Validate a JWT and return the identity, or None on failure.

        On IdP unreachability, logs a warning and returns None (fail-open).
        """
        try:
            signing_key = self._get_signing_key(token)
            if signing_key is None:
                return None

            decode_options = {"verify_aud": self.audience is not None}
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=self.ALLOWED_ALGORITHMS,
                issuer=self.issuer,
                audience=self.audience,
                options=decode_options,
            )

            return OidcIdentity(
                sub=payload["sub"],
                email=payload.get("email"),
                name=payload.get("name"),
                org_id=payload.get(self.org_claim),
                role=payload.get(self.role_claim, "viewer"),
            )

        except jwt.ExpiredSignatureError:
            logger.debug("JWT expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug("JWT validation failed: %s", e)
            return None
        except Exception:
            # IdP unreachable or unexpected error — fail-open with logging (QA: F1)
            logger.warning("OIDC validation error (IdP may be unreachable)", exc_info=True)
            return None

    def _get_signing_key(self, token: str):
        """Get the signing key, with cache-bust-on-miss for key rotation (QA: F2)."""
        try:
            return self._jwk_client.get_signing_key_from_jwt(token)
        except PyJWKClientError:
            # kid not found in cache — try force re-fetch if enough time has passed
            now = time.monotonic()
            if now - self._last_force_fetch < self._MIN_REFETCH_INTERVAL:
                logger.debug("JWKS cache miss but re-fetch throttled")
                return None
            self._last_force_fetch = now
            logger.info("JWKS cache miss — forcing re-fetch for key rotation")
            try:
                # Invalidate cached keys and retry
                self._jwk_client.get_jwk_set(refresh=True)
                return self._jwk_client.get_signing_key_from_jwt(token)
            except Exception:
                logger.warning("JWKS re-fetch failed", exc_info=True)
                return None
        except Exception:
            logger.warning("Failed to get signing key from JWKS", exc_info=True)
            return None
