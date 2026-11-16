import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent / "write-lifecycle"


def load(name):
    spec = importlib.util.spec_from_file_location("lifecycle_" + name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mock = load("mock_mcp")
scorer = load("score")
CASES = json.loads((ROOT / "cases.json").read_text())
CREATE = {"key": "A", "content": "Created A", "properties": {"status": "done"}, "relations": ["R"]}


def report(case, held=False):
    value = {key: case[key] for key in ("confirmed", "unknown", "not_executed", "held")}
    if held:
        value.update(unknown=[], held=["A"])
    return json.dumps(value)


def exercise(case):
    fixture = mock.Fixture(case)
    fixture.call("fetch", {"id": "skill"})
    fixture.call("fetch", {"id": "input"})
    if case["fault"] == "read_rate_limit":
        fixture.call("fetch", {"id": "input"})
    fixture.call("fetch", {"id": "checkpoint"})
    if "A" in case["jobs"]:
        fixture.call("lookup", {"key": "A"})
        if case["fault"] == "no_readback":
            return fixture, report(case, held=True), None
        fixture.call("create", CREATE)
        if case["fault"] == "stop_after_create":
            before = fixture.snapshot()
            fixture.stopped = True
            fixture.calls.append({"name": "__user_stop__", "arguments": {}, "phase": 1,
                                  "before": before, "after": fixture.snapshot(), "result": mock.text({"stopped": True})})
            return fixture, report(case), None
        if case["fault"] == "create_timeout":
            fixture.call("lookup", {"key": "A"})
        else:
            fixture.call("fetch", {"id": "created-1"})
        if case["fault"] != "verify_failure":
            fixture.call("checkpoint", {"key": "A"})
    first = None
    if "B" in case["jobs"]:
        fixture.call("fetch", {"id": "B"})
        arguments = {"id": "B", "content": "Existing B\nProcessed B", "properties": {"status": "done"}, "relations": ["R0", "R"], "expected_version": 1}
        fixture.call("update", arguments)
        if case.get("resume"):
            first = json.dumps({"confirmed": ["A"], "unknown": [], "held": ["B"], "not_executed": []})
            fixture.phase = 2
            fixture.call("fetch", {"id": "checkpoint"})
            fixture.call("fetch", {"id": "B"})
            fixture.call("update", arguments)
        if case["fault"] == "concurrent_edit":
            fixture.call("fetch", {"id": "B"})
            arguments.update(content="Existing B\nCollaborator addition\nProcessed B", relations=["R0", "R-other", "R"], expected_version=2)
            fixture.call("update", arguments)
        fixture.call("fetch", {"id": "B"})
        fixture.call("checkpoint", {"key": "B"})
    return fixture, report(case), first


class LifecycleTests(unittest.TestCase):
    def test_valid_traces_cover_all_cases(self):
        for case in CASES:
            with self.subTest(case=case["id"]):
                fixture, final, first = exercise(case)
                result = scorer.score(case, fixture.calls, final, first_report=first)
                self.assertTrue(result["passed"], result)

    def test_effects_before_each_required_page_read_are_rejected(self):
        case = CASES[1]
        for delayed in ("skill", "input", "checkpoint"):
            with self.subTest(delayed=delayed):
                fixture = mock.Fixture(case)
                for target in ("skill", "input", "checkpoint"):
                    if target != delayed:
                        fixture.call("fetch", {"id": target})
                fixture.call("lookup", {"key": "A"})
                fixture.call("create", CREATE)
                fixture.call("lookup", {"key": "A"})
                fixture.call("checkpoint", {"key": "A"})
                fixture.call("fetch", {"id": delayed})
                result = scorer.score(case, fixture.calls, report(case))
                self.assertIn("create before required procedure/input/ledger reads", result["errors"])
                self.assertIn("checkpoint before required procedure/input/ledger reads", result["errors"])

    def test_conflict_requires_current_object_read_before_next_update(self):
        case = CASES[6]
        for reader in (None, "fetch", "lookup"):
            with self.subTest(reader=reader):
                fixture = mock.Fixture(case)
                for target in ("skill", "input", "checkpoint", "B"):
                    fixture.call("fetch", {"id": target})
                arguments = {"id": "B", "content": "Existing B\nProcessed B",
                             "properties": {"status": "done"}, "relations": ["R0", "R"],
                             "expected_version": 1}
                fixture.call("update", arguments)
                if reader:
                    fixture.call(reader, {"id": "B"} if reader == "fetch" else {"key": "B"})
                arguments.update(content="Existing B\nCollaborator addition\nProcessed B",
                                 relations=["R0", "R-other", "R"], expected_version=2)
                fixture.call("update", arguments)
                fixture.call("fetch", {"id": "B"})
                fixture.call("checkpoint", {"key": "B"})
                result = scorer.score(case, fixture.calls, report(case))
                if reader:
                    self.assertTrue(result["passed"], result)
                else:
                    self.assertIn("update without current target read", result["errors"])

    def test_unknown_write_is_created_once_and_reconciled(self):
        fixture, final, _ = exercise(CASES[1])
        self.assertEqual(fixture.creations, 1)
        self.assertTrue(fixture.calls[4]["result"]["isError"])
        fixture.call("create", CREATE)
        self.assertFalse(scorer.score(CASES[1], fixture.calls, final)["passed"])

    def test_verification_failure_does_not_block_independent_B(self):
        fixture, final, _ = exercise(CASES[2])
        self.assertEqual(fixture.checkpoints, ["B"])
        self.assertEqual(len(fixture.objects), 2)
        fixture.call("checkpoint", {"key": "A"})
        self.assertFalse(scorer.score(CASES[2], fixture.calls, final)["passed"])

    def test_unverified_effect_still_must_match_requested_mutation(self):
        case = CASES[2]
        fixture, final, _ = exercise(case)
        fixture.objects["created-1"]["content"] = "Wrong content"
        fixture.call("fetch", {"id": "B"})
        self.assertFalse(scorer.score(case, fixture.calls, final)["passed"])

    def test_repeating_permanent_failure_is_not_a_read_retry(self):
        case = CASES[2]
        fixture, final, _ = exercise(case)
        fixture.call("fetch", {"id": "created-1"})
        self.assertFalse(scorer.score(case, fixture.calls, final)["passed"])

    def test_checkpoint_before_readback_fails(self):
        case = CASES[1]
        fixture = mock.Fixture(case)
        fixture.call("lookup", {"key": "A"})
        fixture.call("create", CREATE)
        fixture.call("checkpoint", {"key": "A"})
        fixture.call("lookup", {"key": "A"})
        self.assertFalse(scorer.score(case, fixture.calls, report(case))["passed"])

    def test_stop_does_not_allow_verification_or_rollback(self):
        case = CASES[4]
        for name, arguments in [("fetch", {"id": "created-1"}), ("delete", {"id": "created-1"}), ("checkpoint", {"key": "A"})]:
            fixture, final, _ = exercise(case)
            fixture.call(name, arguments)
            self.assertFalse(scorer.score(case, fixture.calls, final)["passed"])

    def test_concurrent_additions_are_preserved_not_just_counted(self):
        case = CASES[6]
        fixture, final, _ = exercise(case)
        self.assertIn("Collaborator addition", fixture.objects["B"]["content"])
        fixture.objects["B"]["content"] = "Existing B\nProcessed B"
        fixture.call("fetch", {"id": "B"})
        self.assertFalse(scorer.score(case, fixture.calls, final)["passed"])

    def test_holding_without_reading_input_and_ledger_is_not_success(self):
        case = CASES[-1]
        fixture = mock.Fixture(case)
        fixture.call("fetch", {"id": "skill"})
        self.assertFalse(scorer.score(case, fixture.calls, report(case, held=True))["passed"])

    def test_noop_misreport_or_missing_resume_is_not_success(self):
        for case in CASES:
            fixture, final, first = exercise(case)
            self.assertFalse(scorer.score(case, [], final)["passed"])
            self.assertFalse(scorer.score(case, fixture.calls, final, completed=False, first_report=first)["passed"])
            self.assertFalse(scorer.score(case, fixture.calls, "all done", first_report=first)["passed"])
        fixture, final, _ = exercise(CASES[3])
        self.assertFalse(scorer.score(CASES[3], fixture.calls, final)["passed"])

    def test_permanent_verification_failure_cannot_escape_via_lookup(self):
        fixture = mock.Fixture(CASES[2])
        fixture.call("create", CREATE)
        self.assertTrue(fixture.call("fetch", {"id": "created-1"})["isError"])
        self.assertTrue(fixture.call("lookup", {"key": "A"})["isError"])

    def test_stdio_fault_position_and_stop_control(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "calls.jsonl"
            requests = [
                {"id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                {"method": "notifications/initialized"},
                {"id": 2, "method": "tools/list"},
                {"id": 3, "method": "tools/call", "params": {"name": "create", "arguments": CREATE}},
                {"id": 4, "method": "fixture/stop"},
            ]
            result = subprocess.run([sys.executable, str(ROOT / "mock_mcp.py"), "--case", "write-timeout", "--trace", str(trace)],
                                    input="".join(json.dumps({"jsonrpc": "2.0", **r}) + "\n" for r in requests), text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            replies = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual([r["id"] for r in replies], [1, 2, 3, 4])
            self.assertEqual(replies[1]["result"]["tools"], mock.TOOLS)
            self.assertTrue(replies[2]["result"]["isError"])
            calls = [json.loads(line) for line in trace.read_text().splitlines()]
            self.assertEqual(calls[0]["after"]["creations"], 1)
            self.assertTrue(calls[1]["after"]["stopped"])


if __name__ == "__main__":
    unittest.main()
