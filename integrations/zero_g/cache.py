"""
Credit-Protection Cache for 0G Private Computer Inferences.
Caches deterministic optimization results locally to avoid duplicate remote API calls
and conserve limited 0G credits.
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import hashlib
import json
import threading
from typing import Any, Dict, Optional
from integrations.zero_g.config import DEFAULT_MODEL, DEFAULT_TRUST_MODE


@dataclass
class CacheEntry:
    value: Any
    created_at: datetime
    expires_at: datetime


class ZeroGCache:
    """Thread-safe LRU/TTL cache for 0G Private Computer inference results."""

    def __init__(self, default_ttl_seconds: int = 3600, max_size: int = 500):
        self.default_ttl = timedelta(seconds=default_ttl_seconds)
        self.max_size = max_size
        self._store: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    @staticmethod
    def compute_key(
        sanitized_prompt: str,
        security_findings: Optional[Dict[str, Any]] = None,
        model: str = DEFAULT_MODEL,
        trust_mode: str = DEFAULT_TRUST_MODE,
        user_id: Optional[str] = None,
        analysis_version: str = "v2_primary",
    ) -> str:
        """
        Derives a deterministic SHA-256 fingerprint scoped by user identity,
        prompt content, security context, model, trust mode, and analysis version.
        Ensures private prompts are never shared across user boundaries.
        """
        scope = f"user:{user_id.strip()}" if user_id and str(user_id).strip() else "scope:isolated"
        serialized_findings = json.dumps(security_findings or {}, sort_keys=True)
        raw_key = f"{scope}||{sanitized_prompt.strip()}||{serialized_findings}||{model}||{trust_mode}||{analysis_version}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Retrieves a non-expired cached result, or None if expired/missing."""
        now = datetime.now(timezone.utc)
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            if entry.expires_at < now:
                del self._store[key]
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Stores a result in the cache with the specified or default TTL."""
        now = datetime.now(timezone.utc)
        ttl = timedelta(seconds=ttl_seconds) if ttl_seconds is not None else self.default_ttl
        with self._lock:
            # Evict oldest entry if at capacity
            if len(self._store) >= self.max_size and key not in self._store:
                oldest_key = min(self._store.keys(), key=lambda k: self._store[k].created_at)
                del self._store[oldest_key]

            self._store[key] = CacheEntry(
                value=value,
                created_at=now,
                expires_at=now + ttl
            )

    def clear(self) -> None:
        """Flushes all cached entries."""
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


# Global singleton cache instance
zero_g_cache = ZeroGCache()

