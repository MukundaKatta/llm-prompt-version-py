# llm-prompt-version-py

Version and hash LLM prompt templates. Track prompt evolution, detect drift, and look up prompts by content hash.

It is a tiny, dependency-free library (standard library only) for keeping
your system/instruction prompts under control:

- **Content addressing** — every prompt gets a stable SHA-256 hash so you can
  pin, compare, and look prompts up by content.
- **Versioning** — store multiple named versions (semver, dates, anything)
  in a single store and fetch the latest or any specific one.
- **Drift detection** — assert at runtime that a prompt still matches the
  version you reviewed, and catch silent edits.
- **Variable rendering** — fill `{placeholder}` templates and emit ready-to-send
  chat message dicts.

## Install

```bash
pip install llm-prompt-version-py
```

Requires Python 3.9 or newer. No third-party dependencies.

## Usage

```python
from llm_prompt_version import PromptVersionStore, hash_prompt, short_hash

store = PromptVersionStore(name="system_prompt")
store.add("1.0.0", "You are a helpful assistant.")
store.add("1.1.0", "You are a helpful assistant. Be concise.")

pv = store.get("1.0.0")
print(pv.hash)          # SHA-256
print(pv.short_hash)    # first 8 hex chars

latest = store.latest()
print(latest.version)   # "1.1.0"

# Detect drift
if store.has_changed("1.0.0", current_prompt_text):
    print("Prompt has been modified!")

# Variable rendering
store.add("2.0.0", "You are a {role} assistant.")
msg = store.get("2.0.0").as_message({"role": "coding"})

# Diff between versions
diff = store.diff_summary("1.0.0", "1.1.0")
print(diff["char_delta"])

# Lookup by hash prefix
pv = store.by_hash("a1b2c3d4")
```

## API reference

### Functions

| Function | Description |
| --- | --- |
| `hash_prompt(text, algorithm="sha256") -> str` | Hex digest of `text` (UTF-8 encoded). Raises `ValueError` for an unknown algorithm. |
| `short_hash(text, length=8) -> str` | First `length` hex characters of the SHA-256 hash of `text`. |

### `PromptVersion`

A dataclass representing one versioned snapshot of a prompt.

| Member | Description |
| --- | --- |
| `version: str` | The version identifier. |
| `text: str` | The raw prompt template. |
| `hash: str` | Full SHA-256 hex digest of `text`. |
| `created_at: float` | Unix timestamp set when the object was created. |
| `description: str` | Optional human-readable note. |
| `metadata: dict` | Optional arbitrary metadata. |
| `short_hash -> str` | Property: first 8 hex chars of `hash`. |
| `render(variables=None) -> str` | Render `{placeholder}` templates with a mapping. If rendering fails (missing/positional/attribute fields) the original text is returned unchanged. |
| `as_message(variables=None) -> dict` | `{"role": "system", "content": render(variables)}`. |

### `PromptVersionStore`

A container for multiple `PromptVersion` objects.

| Method | Description |
| --- | --- |
| `PromptVersionStore(name="default")` | Create a store. |
| `add(version, text, description="", metadata=None) -> PromptVersion` | Add or replace a version; returns it. |
| `get(version) -> PromptVersion` | Fetch a version; raises `KeyError` if missing. |
| `get_or_none(version) -> PromptVersion \| None` | Fetch a version or `None`. |
| `by_hash(h) -> PromptVersion \| None` | Look up by full hash or hash prefix (deterministic). |
| `latest() -> PromptVersion \| None` | Most recently added version, or `None`. |
| `all_versions() -> list[PromptVersion]` | All versions in insertion order. |
| `version_names() -> list[str]` | Version strings in insertion order. |
| `has_changed(version, current_text) -> bool` | `True` if the stored text differs from `current_text` (or the version is unknown). |
| `diff_summary(v1, v2) -> dict` | `same_hash`, char counts, and `char_delta` between two versions. |
| `len(store)`, `version in store` | Number of versions / membership test. |

## Development

The test suite uses only the standard library, so no extra packages are
needed:

```bash
pip install -e .
python -m unittest discover -s tests -v
```

## License

MIT
