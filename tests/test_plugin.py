import unittest
from unittest.mock import patch

import __init__ as plugin
from clawprint_plugin.commands import handle_command
from clawprint_plugin.tools import payload_hash, preview, verify_record


class PluginTests(unittest.TestCase):
    def test_preview_is_deterministic_and_local(self):
        state = {}
        result = preview({"title": "A note", "content": "line one\r\nline two", "tags": [" agents "]}, state=state, now=10)
        self.assertTrue(result["preview"])
        self.assertFalse(result["network_performed"])
        self.assertEqual(result["payload"]["content"], "line one\nline two")
        self.assertIn("proposal:" + result["proposal_hash"], state)

    def test_hash_changes_with_content_and_verifies_exact_payload(self):
        first = {"title": "A", "content": "one", "tags": []}
        second = {"title": "A", "content": "two", "tags": []}
        self.assertNotEqual(payload_hash(first), payload_hash(second))
        self.assertTrue(verify_record({**first, "expected_hash": payload_hash(first)})["matches"])
        self.assertFalse(verify_record({**second, "expected_hash": payload_hash(first)})["matches"])

    def test_human_command_rejects_missing_confirmation_and_expiry(self):
        state = {}
        result = preview({"title": "A", "content": "body", "tags": []}, state=state, ttl_seconds=1, now=0)
        self.assertFalse(handle_command("publish " + result["proposal_hash"], state=state, now=0)["ok"])
        self.assertFalse(handle_command("publish " + result["proposal_hash"] + " --confirm", state=state, now=2)["ok"])

    def test_publish_is_one_use_after_exact_confirmation(self):
        state = {}
        result = preview({"title": "A", "content": "body", "tags": []}, state=state, now=0)
        with patch.dict("os.environ", {"CLAWPRINT_API_KEY": "test-key"}), patch(
            "clawprint_plugin.commands._publish", return_value={"url": "https://clawprint.org/p/a"}
        ) as publish:
            sent = handle_command("publish " + result["proposal_hash"] + " --confirm", state=state, now=1)
        self.assertTrue(sent["ok"])
        publish.assert_called_once()
        self.assertFalse(handle_command("publish " + result["proposal_hash"] + " --confirm", state=state, now=1)["ok"])

    def test_registration_has_two_tools_and_one_human_command(self):
        class Context:
            def __init__(self):
                self.state = {}
                self.tools = []
                self.commands = []

            def get_config(self, _name, default=None):
                return default

            def register_tool(self, **kwargs):
                self.tools.append(kwargs)

            def register_command(self, *args, **kwargs):
                self.commands.append((args, kwargs))

        context = Context()
        plugin.register(context)
        self.assertEqual([tool["name"] for tool in context.tools], ["clawprint_preview", "clawprint_verify_record"])
        self.assertEqual(context.commands[0][0][0], "clawprint")


if __name__ == "__main__":
    unittest.main()
