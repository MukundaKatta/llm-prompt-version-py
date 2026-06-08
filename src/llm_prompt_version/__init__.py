"""llm-prompt-version-py — version and hash LLM prompt templates."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


def hash_prompt(text: str, algorithm: str = "sha256") -> str:
    """Return a hex digest of the prompt text."""
    h = hashlib.new(algorithm)
    h.update(text.encode())
    return h.hexdigest()


def short_hash(text: str, length: int = 8) -> str:
    """Return the first *length* hex chars of the SHA-256 hash."""
    return hash_prompt(text)[:length]


@dataclass
class PromptVersion:
    """A versioned snapshot of a prompt template."""

    version: str
    text: str
    hash: str
    created_at: float = field(default_factory=time.time)
    description: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def short_hash(self) -> str:
        return self.hash[:8]

    def render(self, variables: dict[str, Any] | None = None) -> str:
        """Render the template with optional variable substitution."""
        if not variables:
            return self.text
        try:
            return self.text.format_map(variables)
        except (KeyError, IndexError, ValueError, AttributeError, TypeError):
            return self.text

    def as_message(self, variables: dict[str, Any] | None = None) -> dict:
        """Return a system message dict with the rendered content."""
        return {"role": "system", "content": self.render(variables)}


class PromptVersionStore:
    """
    Store and retrieve versioned prompt templates.

    Versions are identified by a version string (e.g. semver or timestamp).
    Each prompt is also content-addressed by hash for exact-match lookup.

    Example::

        store = PromptVersionStore(name="system_prompt")
        store.add("1.0.0", "You are a helpful assistant.")
        store.add("1.1.0", "You are a helpful assistant. Be concise.")

        v = store.get("1.0.0")
        print(v.version, v.hash)

        latest = store.latest()
        print(latest.version)

        # Detect drift
        if store.has_changed("1.0.0", "You are a helpful assistant."):
            print("Prompt text has changed!")
    """

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self._versions: dict[str, PromptVersion] = {}
        self._by_hash: dict[str, PromptVersion] = {}
        self._order: list[str] = []

    def add(
        self,
        version: str,
        text: str,
        description: str = "",
        metadata: dict | None = None,
    ) -> PromptVersion:
        """Add a new prompt version."""
        h = hash_prompt(text)
        pv = PromptVersion(
            version=version,
            text=text,
            hash=h,
            description=description,
            metadata=metadata or {},
        )
        self._versions[version] = pv
        self._by_hash[h] = pv
        if version not in self._order:
            self._order.append(version)
        return pv

    def get(self, version: str) -> PromptVersion:
        """Get a prompt version by version string."""
        if version not in self._versions:
            raise KeyError(f"Version '{version}' not found in store '{self.name}'.")
        return self._versions[version]

    def get_or_none(self, version: str) -> PromptVersion | None:
        return self._versions.get(version)

    def by_hash(self, h: str) -> PromptVersion | None:
        """Look up a version by its full or prefix hash."""
        if not h:
            return None
        if h in self._by_hash:
            return self._by_hash[h]
        for key, pv in self._by_hash.items():
            if key.startswith(h):
                return pv
        return None

    def latest(self) -> PromptVersion | None:
        """Return the most recently added version."""
        if not self._order:
            return None
        return self._versions[self._order[-1]]

    def all_versions(self) -> list[PromptVersion]:
        """Return all versions in insertion order."""
        return [self._versions[v] for v in self._order]

    def version_names(self) -> list[str]:
        """Return version strings in insertion order."""
        return list(self._order)

    def has_changed(self, version: str, current_text: str) -> bool:
        """Return True if the stored prompt text differs from current_text."""
        pv = self.get_or_none(version)
        if pv is None:
            return True  # version not found → treat as changed
        return pv.hash != hash_prompt(current_text)

    def diff_summary(self, v1: str, v2: str) -> dict:
        """Return a summary of differences between two versions."""
        pv1 = self.get(v1)
        pv2 = self.get(v2)
        return {
            "v1": v1,
            "v2": v2,
            "same_hash": pv1.hash == pv2.hash,
            "v1_chars": len(pv1.text),
            "v2_chars": len(pv2.text),
            "char_delta": len(pv2.text) - len(pv1.text),
        }

    def __len__(self) -> int:
        return len(self._versions)

    def __contains__(self, version: str) -> bool:
        return version in self._versions


__all__ = ["PromptVersion", "PromptVersionStore", "hash_prompt", "short_hash"]
