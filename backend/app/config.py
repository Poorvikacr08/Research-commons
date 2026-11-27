"""Small environment-backed settings with safe startup validation."""

import os
from collections.abc import Mapping


def load_jwt_secret(environment: Mapping[str, str] | None = None) -> str:
    """Return a configured JWT secret or fail before the API starts unsafely."""
    source = os.environ if environment is None else environment
    secret = source.get("JWT_SECRET", "")
    if (
        not secret
        or secret == "dev-only-secret-change-me"
        or secret.startswith("replace_with_")
        or len(secret) < 32
    ):
        raise RuntimeError(
            "JWT_SECRET must be a private random value of at least 32 characters before starting the API."
        )
    return secret
