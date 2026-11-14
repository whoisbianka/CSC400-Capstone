"""Resolve Secret Manager references at startup without writing secrets to disk."""
import os
from functools import lru_cache

from google.cloud import secretmanager


@lru_cache(maxsize=16)
def read_secret(secret_version):
    """Retrieve and cache one secret version for this Python process."""
    if not isinstance(secret_version, str) or not secret_version.strip():
        raise RuntimeError("A Secret Manager version path is required.")

    with secretmanager.SecretManagerServiceClient() as client:
        response = client.access_secret_version(
            request={"name": secret_version},
            timeout=15,
        )

    value = response.payload.data.decode("utf-8")
    if not value.strip():
        raise RuntimeError("Secret Manager returned an empty secret.")
    return value


def load_application_secrets():
    """Load configured references into the environment expected by the app."""
    mappings = {
        "GEMINI_API_KEY": "GEMINI_API_KEY_SECRET_VERSION",
        "CLERK_SECRET_KEY": "CLERK_SECRET_KEY_SECRET_VERSION",
        "CLERK_PUBLISHABLE_KEY": "CLERK_PUBLISHABLE_KEY_SECRET_VERSION",
        "SECRET_KEY": "SECRET_KEY_SECRET_VERSION",
    }
    references = {}
    for destination, reference in mappings.items():
        version = os.environ.get(reference, "").strip()
        if not version:
            raise RuntimeError(f"{reference} is required.")
        references[destination] = version

    # Do not partially replace the environment if any secret cannot be read.
    resolved = {key: read_secret(version) for key, version in references.items()}
    os.environ.update(resolved)
