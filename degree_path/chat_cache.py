"""Short-lived, process-local cache for the shared chat keyword catalog."""

from copy import deepcopy
from threading import Lock
from time import monotonic


class KeywordCatalogCache:
    def __init__(self, ttl_seconds=300):
        self.ttl_seconds = ttl_seconds
        self._rows = None
        self._expires_at = 0.0
        self._lock = Lock()

    def get(self, loader):
        # Only one thread loads an expired catalog; others reuse its result.
        with self._lock:
            if self._rows is None or monotonic() >= self._expires_at:
                rows = loader()
                # Failed loads are not cached. Expiration starts after loading.
                self._rows = deepcopy(rows)
                self._expires_at = monotonic() + self.ttl_seconds
            # Callers cannot accidentally modify the shared cached catalog.
            return deepcopy(self._rows)
