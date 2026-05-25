# llm-prompt-version-py

Version and hash LLM prompt templates. Track prompt evolution, detect drift, and look up prompts by content hash.

## Install

```bash
pip install llm-prompt-version-py
```

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

## License

MIT
