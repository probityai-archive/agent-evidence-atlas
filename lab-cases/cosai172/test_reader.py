"""Consumer controls over committed fixtures; expectations never enter the reader."""

import copy
import json
from pathlib import Path
import unittest

from reader import REQUIRED, can_replay, read_record, string_values


class ConsumerChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(Path(__file__).with_name("cases.json").read_text())
        cls.case = cls.data["cases"][0]
        cls.grant = cls.data["fixture_grant"]

    def test_committed_cases(self):
        for case in self.data["cases"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(
                    read_record(case["record"], case["observation"], self.grant),
                    case["expected"],
                )

    def test_each_required_row_is_per_record(self):
        for key in REQUIRED:
            record = copy.deepcopy(self.case["record"])
            del record[key]
            with self.subTest(missing=key):
                self.assertEqual(read_record(record, self.case["observation"], self.grant),
                                 {"result": "processing_failure", "reason": "record_fields"})

    def test_union_does_not_repair_two_records(self):
        record = self.case["record"]
        keys = sorted(REQUIRED)
        a = {key: record[key] for key in keys[:6]}
        b = {key: record[key] for key in keys[6:]}
        self.assertEqual(set(a) | set(b), REQUIRED)
        for part in (a, b):
            self.assertEqual(read_record(part, self.case["observation"], self.grant),
                             {"result": "processing_failure", "reason": "record_fields"})
        # Positive control: the fixture's complete logical record is readable.
        self.assertEqual(read_record(a | b, self.case["observation"], self.grant),
                         self.case["expected"])

    def test_missing_and_empty_values_are_processing_failures(self):
        for value in (None, False, 0, [], "", {}):
            record = copy.deepcopy(self.case["record"])
            record["policy_version"] = value
            with self.subTest(value=value):
                self.assertEqual(read_record(record, self.case["observation"], self.grant),
                                 {"result": "processing_failure", "reason": "empty_or_invalid_field"})
        for record in (None, [], "record", {**self.case["record"], "unexpected": "x"}):
            self.assertEqual(read_record(record, self.case["observation"], self.grant),
                             {"result": "processing_failure", "reason": "record_fields"})

    def test_runtime_shape_and_native_value(self):
        for value in ("absent", {}, {"state": "absent"},
                      {"state": "missing", "value": "x", "reason": "x"},
                      {"state": "absent", "value": True, "reason": "x"},
                      {"state": "absent", "value": "not-available", "reason": ""}):
            record = copy.deepcopy(self.case["record"])
            record["runtime_identity_or_attestation_reference"] = value
            result = read_record(record, self.case["observation"], self.grant)
            self.assertEqual(result["result"], "processing_failure")
        record = copy.deepcopy(self.case["record"])
        record["runtime_identity_or_attestation_reference"]["value"] = "unknown"
        self.assertEqual(read_record(record, self.case["observation"], self.grant),
                         {"result": "processing_failure", "reason": "runtime_absence_value"})
        record = copy.deepcopy(self.data["cases"][1]["record"])
        record["runtime_identity_or_attestation_reference"]["value"] = "not-available"
        self.assertEqual(read_record(record, self.data["cases"][1]["observation"], self.grant),
                         {"result": "processing_failure", "reason": "runtime_unknown_value"})

    def test_context_shape_binding_and_reverse_conflation(self):
        for context in (None, {}, [],
                        {"action_identifier": "another-action", "availability": "unavailable"},
                        {"action_identifier": "fixture:action-001", "availability": []},
                        {"action_identifier": "fixture:action-001", "availability": True},
                        {"action_identifier": "fixture:action-001", "availability": "absent"}):
            self.assertEqual(read_record(self.case["record"], context, self.grant),
                             {"result": "processing_failure", "reason": "fixture_observation_context"})
        unknown = self.data["cases"][1]
        self.assertEqual(read_record(unknown["record"], self.case["observation"], self.grant),
                         {"result": "refused", "reason": "unsupported_runtime_observation"})

    def test_exact_grant_can_replay_digest_cannot(self):
        unsafe = self.data["cases"][3]["record"]
        self.assertTrue(can_replay(unsafe, self.grant))
        self.assertFalse(can_replay(self.case["record"], self.grant))
        for key in REQUIRED:
            record = copy.deepcopy(self.case["record"])
            record[key] = {"nested": [False, {"capability": self.grant}]}
            with self.subTest(field=key):
                self.assertEqual(read_record(record, self.case["observation"], self.grant),
                                 {"result": "refused", "reason": "replayable_fixture_authority"})
        self.assertEqual(string_values({self.grant: 7}), [])

    def test_pending_outcome_is_not_reclassified(self):
        record = self.case["record"]
        before = copy.deepcopy(record)
        self.assertEqual(record["outcome"]["state"], "pending")
        self.assertEqual(read_record(record, self.case["observation"], self.grant),
                         self.case["expected"])
        self.assertEqual(record, before)
        self.assertEqual(record["outcome"]["state"], "pending")


if __name__ == "__main__":
    unittest.main()
