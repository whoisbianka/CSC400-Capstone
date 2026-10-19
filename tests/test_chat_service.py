"""Offline contract tests: no API credentials or database connection required."""

import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from degree_path.chat_service import InvalidAdvisorResponse, interpret_message


class ChatServiceTests(unittest.TestCase):
    def setUp(self):
        self.catalog = [{"keyword_id": 7, "keyword": "Biology"}]
        self.reply = {
            "reply": "What parts of biology interest you?",
            "keyword_additions": [{"keyword": "Biology", "evidence": "I enjoy biology"}],
            "keyword_removals": [],
            "major_mentions": [],
        }

    def call_service(self, payload, saved=None):
        self.client = Mock()
        self.client.models.generate_content.return_value = SimpleNamespace(text=payload)
        return interpret_message(
            "I enjoy biology", self.catalog, saved or [], [],
            client=self.client, model="test-model",
        )

    def test_valid_turn_and_request_context(self):
        turn = self.call_service(json.dumps(self.reply))
        self.assertEqual(turn.keyword_additions[0].keyword_id, 7)
        args = self.client.models.generate_content.call_args.kwargs
        context = json.loads(args["contents"])
        self.assertEqual(context["latest_message"], "I enjoy biology")
        self.assertEqual(context["recent_messages"], [])
        self.assertIn("one clear question", args["config"].system_instruction)

    def test_invalid_responses_are_rejected(self):
        for payload in (None, "not JSON", "{}"):
            with self.subTest(payload=payload), self.assertRaises(InvalidAdvisorResponse):
                self.call_service(payload)
        
    def test_unknown_name_and_invented_evidence_are_rejected(self):
        for item in (
            {"keyword": "Not in catalog", "evidence": "I enjoy biology"},
            {"keyword": "Biology", "evidence": "I love science"},
            {"keyword": 7, "evidence": "I enjoy biology"},
        ):
            with self.subTest(item=item):
                with self.assertRaises(InvalidAdvisorResponse):
                    self.call_service(
                        json.dumps({
                            **self.reply,
                            "keyword_additions": [item],
                        })
                    )

    def test_conflicting_changes_are_rejected(self):
        with self.assertRaises(InvalidAdvisorResponse):
            self.call_service(json.dumps({**self.reply, "keyword_removals": ["Biology"]}), self.catalog)

    def test_existing_additions_can_update_evidence(self):
        turn = self.call_service(json.dumps(self.reply), self.catalog)

        self.assertEqual(len(turn.keyword_additions), 1)
        self.assertEqual(turn.keyword_additions[0].keyword_id, 7)
        self.assertEqual(
            turn.keyword_additions[0].evidence,
            "I enjoy biology",
        )

    def test_only_saved_keywords_can_be_removed(self):
        payload = json.dumps({**self.reply, "keyword_additions": [], "keyword_removals": ["Biology"]})
        with self.assertRaises(InvalidAdvisorResponse):
            self.call_service(payload)
        self.assertEqual(self.call_service(payload, self.catalog).keyword_removals, [7])

    def test_provider_failure_propagates(self):
        client = Mock()
        client.models.generate_content.side_effect = TimeoutError("provider timeout")
        with self.assertRaises(TimeoutError):
            interpret_message("Hello", self.catalog, [], [], client=client, model="test")

    def test_import_does_not_load_database_module(self):
        result = subprocess.run(
            [sys.executable, "-c", "import degree_path.chat_service; import sys; assert 'db_functions' not in sys.modules"],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
