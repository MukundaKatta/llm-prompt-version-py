"""Tests for llm-prompt-version-py."""
import pytest
from llm_prompt_version import (
    PromptVersion, PromptVersionStore, hash_prompt, short_hash
)


def test_hash_prompt_stable():
    h1 = hash_prompt("Hello world")
    h2 = hash_prompt("Hello world")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256


def test_hash_prompt_different():
    assert hash_prompt("Hello") != hash_prompt("World")


def test_short_hash_length():
    h = short_hash("Hello world", length=8)
    assert len(h) == 8


def test_short_hash_default_length():
    h = short_hash("Hello world")
    assert len(h) == 8


def test_prompt_version_render_no_vars():
    pv = PromptVersion(version="1.0", text="Hello!", hash=hash_prompt("Hello!"))
    assert pv.render() == "Hello!"


def test_prompt_version_render_with_vars():
    pv = PromptVersion(version="1.0", text="Hello {name}!", hash=hash_prompt("Hello {name}!"))
    assert pv.render({"name": "Alice"}) == "Hello Alice!"


def test_prompt_version_render_missing_var_passthrough():
    pv = PromptVersion(version="1.0", text="Hello {x}!", hash=hash_prompt("Hello {x}!"))
    result = pv.render({"other": "y"})
    assert "{x}" in result


def test_prompt_version_as_message():
    pv = PromptVersion(version="1.0", text="You are helpful.", hash=hash_prompt("You are helpful."))
    msg = pv.as_message()
    assert msg == {"role": "system", "content": "You are helpful."}


def test_prompt_version_short_hash():
    pv = PromptVersion(version="1.0", text="hi", hash=hash_prompt("hi"))
    assert len(pv.short_hash) == 8


def test_store_add_and_get():
    store = PromptVersionStore("test")
    store.add("1.0.0", "You are helpful.")
    pv = store.get("1.0.0")
    assert pv.version == "1.0.0"
    assert pv.text == "You are helpful."
    assert len(pv.hash) == 64


def test_store_get_missing_raises():
    store = PromptVersionStore()
    with pytest.raises(KeyError) as exc_info:
        store.get("missing")
    assert "missing" in str(exc_info.value)


def test_store_get_or_none():
    store = PromptVersionStore()
    assert store.get_or_none("x") is None
    store.add("x", "text")
    assert store.get_or_none("x") is not None


def test_store_latest():
    store = PromptVersionStore()
    assert store.latest() is None
    store.add("1.0", "first")
    store.add("2.0", "second")
    assert store.latest().version == "2.0"


def test_store_version_names():
    store = PromptVersionStore()
    store.add("1.0", "A")
    store.add("2.0", "B")
    assert store.version_names() == ["1.0", "2.0"]


def test_store_all_versions():
    store = PromptVersionStore()
    store.add("1.0", "A")
    store.add("2.0", "B")
    versions = store.all_versions()
    assert len(versions) == 2
    assert versions[0].version == "1.0"


def test_store_has_changed_false():
    store = PromptVersionStore()
    store.add("1.0", "You are helpful.")
    assert store.has_changed("1.0", "You are helpful.") is False


def test_store_has_changed_true():
    store = PromptVersionStore()
    store.add("1.0", "You are helpful.")
    assert store.has_changed("1.0", "You are a bot.") is True


def test_store_has_changed_missing_version():
    store = PromptVersionStore()
    assert store.has_changed("missing", "any text") is True


def test_store_by_hash():
    store = PromptVersionStore()
    pv = store.add("1.0", "Hello!")
    found = store.by_hash(pv.hash)
    assert found is not None
    assert found.version == "1.0"


def test_store_by_hash_prefix():
    store = PromptVersionStore()
    pv = store.add("1.0", "Hello!")
    found = store.by_hash(pv.hash[:8])
    assert found is not None


def test_store_by_hash_missing():
    store = PromptVersionStore()
    assert store.by_hash("nonexistent") is None


def test_store_len():
    store = PromptVersionStore()
    assert len(store) == 0
    store.add("1.0", "A")
    store.add("2.0", "B")
    assert len(store) == 2


def test_store_contains():
    store = PromptVersionStore()
    store.add("1.0", "A")
    assert "1.0" in store
    assert "2.0" not in store


def test_store_diff_summary():
    store = PromptVersionStore()
    store.add("1.0", "Short.")
    store.add("2.0", "Much longer text here.")
    diff = store.diff_summary("1.0", "2.0")
    assert diff["v1"] == "1.0"
    assert diff["v2"] == "2.0"
    assert diff["same_hash"] is False
    assert diff["char_delta"] > 0


def test_store_metadata():
    store = PromptVersionStore()
    pv = store.add("1.0", "Text", metadata={"author": "Alice"})
    assert pv.metadata["author"] == "Alice"


def test_store_description():
    store = PromptVersionStore()
    pv = store.add("1.0", "Text", description="Initial version")
    assert pv.description == "Initial version"
