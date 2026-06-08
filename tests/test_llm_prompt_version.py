"""Tests for llm-prompt-version-py.

These tests use only the Python standard library ``unittest`` so they run
with no third-party dependencies::

    python3 -m unittest discover -s tests
"""

import unittest

from llm_prompt_version import (
    PromptVersion,
    PromptVersionStore,
    hash_prompt,
    short_hash,
)


class HashPromptTests(unittest.TestCase):
    def test_hash_prompt_stable(self):
        h1 = hash_prompt("Hello world")
        h2 = hash_prompt("Hello world")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)  # SHA-256 hex digest length

    def test_hash_prompt_different(self):
        self.assertNotEqual(hash_prompt("Hello"), hash_prompt("World"))

    def test_hash_prompt_algorithm(self):
        h = hash_prompt("Hello world", algorithm="sha1")
        self.assertEqual(len(h), 40)  # SHA-1 hex digest length
        self.assertEqual(h, hash_prompt("Hello world", algorithm="sha1"))

    def test_hash_prompt_unicode(self):
        # Non-ASCII text must hash deterministically.
        h1 = hash_prompt("héllo · 世界 · 🤖")
        h2 = hash_prompt("héllo · 世界 · 🤖")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_hash_prompt_empty(self):
        # Known SHA-256 of the empty string.
        self.assertEqual(
            hash_prompt(""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    def test_short_hash_length(self):
        self.assertEqual(len(short_hash("Hello world", length=8)), 8)

    def test_short_hash_default_length(self):
        self.assertEqual(len(short_hash("Hello world")), 8)

    def test_short_hash_is_prefix_of_full_hash(self):
        text = "You are helpful."
        self.assertTrue(hash_prompt(text).startswith(short_hash(text)))


class PromptVersionTests(unittest.TestCase):
    def test_render_no_vars(self):
        pv = PromptVersion(version="1.0", text="Hello!", hash=hash_prompt("Hello!"))
        self.assertEqual(pv.render(), "Hello!")

    def test_render_with_vars(self):
        pv = PromptVersion(
            version="1.0", text="Hello {name}!", hash=hash_prompt("Hello {name}!")
        )
        self.assertEqual(pv.render({"name": "Alice"}), "Hello Alice!")

    def test_render_empty_vars_dict(self):
        pv = PromptVersion(
            version="1.0", text="Hello {name}!", hash=hash_prompt("Hello {name}!")
        )
        # An empty mapping is falsy, so the template is returned verbatim.
        self.assertEqual(pv.render({}), "Hello {name}!")

    def test_render_missing_var_passthrough(self):
        pv = PromptVersion(
            version="1.0", text="Hello {x}!", hash=hash_prompt("Hello {x}!")
        )
        self.assertIn("{x}", pv.render({"other": "y"}))

    def test_render_attribute_template_passthrough(self):
        # Attribute access on an incompatible value must not crash.
        pv = PromptVersion(
            version="1.0", text="Hi {x.y}!", hash=hash_prompt("Hi {x.y}!")
        )
        self.assertEqual(pv.render({"x": "str"}), "Hi {x.y}!")

    def test_render_positional_template_passthrough(self):
        # Positional fields cannot resolve against a mapping; pass through.
        pv = PromptVersion(version="1.0", text="Hi {0}!", hash=hash_prompt("Hi {0}!"))
        self.assertEqual(pv.render({"name": "Alice"}), "Hi {0}!")

    def test_as_message(self):
        pv = PromptVersion(
            version="1.0",
            text="You are helpful.",
            hash=hash_prompt("You are helpful."),
        )
        self.assertEqual(
            pv.as_message(), {"role": "system", "content": "You are helpful."}
        )

    def test_as_message_with_vars(self):
        pv = PromptVersion(
            version="1.0",
            text="You are a {role} assistant.",
            hash=hash_prompt("You are a {role} assistant."),
        )
        msg = pv.as_message({"role": "coding"})
        self.assertEqual(
            msg, {"role": "system", "content": "You are a coding assistant."}
        )

    def test_short_hash_property(self):
        pv = PromptVersion(version="1.0", text="hi", hash=hash_prompt("hi"))
        self.assertEqual(len(pv.short_hash), 8)
        self.assertTrue(pv.hash.startswith(pv.short_hash))


class PromptVersionStoreTests(unittest.TestCase):
    def test_add_and_get(self):
        store = PromptVersionStore("test")
        store.add("1.0.0", "You are helpful.")
        pv = store.get("1.0.0")
        self.assertEqual(pv.version, "1.0.0")
        self.assertEqual(pv.text, "You are helpful.")
        self.assertEqual(len(pv.hash), 64)

    def test_add_returns_version(self):
        store = PromptVersionStore()
        pv = store.add("1.0", "Text")
        self.assertIsInstance(pv, PromptVersion)
        self.assertEqual(pv.version, "1.0")

    def test_get_missing_raises_keyerror(self):
        store = PromptVersionStore()
        with self.assertRaises(KeyError) as ctx:
            store.get("missing")
        self.assertIn("missing", str(ctx.exception))

    def test_get_or_none(self):
        store = PromptVersionStore()
        self.assertIsNone(store.get_or_none("x"))
        store.add("x", "text")
        self.assertIsNotNone(store.get_or_none("x"))

    def test_latest(self):
        store = PromptVersionStore()
        self.assertIsNone(store.latest())
        store.add("1.0", "first")
        store.add("2.0", "second")
        self.assertEqual(store.latest().version, "2.0")

    def test_version_names(self):
        store = PromptVersionStore()
        store.add("1.0", "A")
        store.add("2.0", "B")
        self.assertEqual(store.version_names(), ["1.0", "2.0"])

    def test_all_versions(self):
        store = PromptVersionStore()
        store.add("1.0", "A")
        store.add("2.0", "B")
        versions = store.all_versions()
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].version, "1.0")

    def test_re_add_same_version_updates_in_place(self):
        # Re-adding a known version replaces its content without duplicating
        # the entry in the insertion order.
        store = PromptVersionStore()
        store.add("1.0", "first")
        store.add("1.0", "second")
        self.assertEqual(store.version_names(), ["1.0"])
        self.assertEqual(store.get("1.0").text, "second")
        self.assertEqual(len(store), 1)

    def test_has_changed_false(self):
        store = PromptVersionStore()
        store.add("1.0", "You are helpful.")
        self.assertFalse(store.has_changed("1.0", "You are helpful."))

    def test_has_changed_true(self):
        store = PromptVersionStore()
        store.add("1.0", "You are helpful.")
        self.assertTrue(store.has_changed("1.0", "You are a bot."))

    def test_has_changed_missing_version(self):
        store = PromptVersionStore()
        self.assertTrue(store.has_changed("missing", "any text"))

    def test_by_hash_full(self):
        store = PromptVersionStore()
        pv = store.add("1.0", "Hello!")
        found = store.by_hash(pv.hash)
        self.assertIsNotNone(found)
        self.assertEqual(found.version, "1.0")

    def test_by_hash_prefix(self):
        store = PromptVersionStore()
        pv = store.add("1.0", "Hello!")
        found = store.by_hash(pv.hash[:8])
        self.assertIsNotNone(found)
        self.assertEqual(found.version, "1.0")

    def test_by_hash_missing(self):
        store = PromptVersionStore()
        self.assertIsNone(store.by_hash("nonexistent"))

    def test_by_hash_empty_returns_none(self):
        store = PromptVersionStore()
        store.add("1.0", "Hello!")
        store.add("2.0", "World!")
        self.assertIsNone(store.by_hash(""))

    def test_len(self):
        store = PromptVersionStore()
        self.assertEqual(len(store), 0)
        store.add("1.0", "A")
        store.add("2.0", "B")
        self.assertEqual(len(store), 2)

    def test_contains(self):
        store = PromptVersionStore()
        store.add("1.0", "A")
        self.assertIn("1.0", store)
        self.assertNotIn("2.0", store)

    def test_diff_summary(self):
        store = PromptVersionStore()
        store.add("1.0", "Short.")
        store.add("2.0", "Much longer text here.")
        diff = store.diff_summary("1.0", "2.0")
        self.assertEqual(diff["v1"], "1.0")
        self.assertEqual(diff["v2"], "2.0")
        self.assertFalse(diff["same_hash"])
        self.assertGreater(diff["char_delta"], 0)

    def test_diff_summary_identical_text(self):
        store = PromptVersionStore()
        store.add("1.0", "Same text.")
        store.add("1.0-copy", "Same text.")
        diff = store.diff_summary("1.0", "1.0-copy")
        self.assertTrue(diff["same_hash"])
        self.assertEqual(diff["char_delta"], 0)

    def test_metadata(self):
        store = PromptVersionStore()
        pv = store.add("1.0", "Text", metadata={"author": "Alice"})
        self.assertEqual(pv.metadata["author"], "Alice")

    def test_description(self):
        store = PromptVersionStore()
        pv = store.add("1.0", "Text", description="Initial version")
        self.assertEqual(pv.description, "Initial version")

    def test_independent_stores_do_not_share_state(self):
        # Mutable default fields must not leak between instances.
        a = PromptVersionStore("a")
        b = PromptVersionStore("b")
        a.add("1.0", "only in a")
        self.assertIn("1.0", a)
        self.assertNotIn("1.0", b)
        self.assertEqual(len(b), 0)


if __name__ == "__main__":
    unittest.main()
