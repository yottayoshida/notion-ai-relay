import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent / "compatibility"
BUNDLE = ROOT.parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location("compat_" + name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


mock = load("mock_mcp")
scorer = load("score")
calc = load("calculations")
CASES = json.loads((ROOT / "cases.json").read_text())


def exercise(case):
    fixture = mock.Fixture(case, BUNDLE)
    for name in mock.LOCAL_FILES:
        fixture.call("relay_file", {"path": name})
    if case["mode"] != "loading":
        fixture.call("get_access", {})
    if case.get("listing"):
        for scope in ("workspace", "favorites"):
            fixture.call("list_agents", {"scope": scope})
        if case.get("require_next_page"):
            fixture.call("list_agents", {"scope": "workspace", "cursor": "next-page"})
    if case.get("settings"):
        fixture.call("get_settings", {"agent_url": "agent://fixture/editor"})
    for target in case["reads"]:
        fixture.call("fetch", {"id": target})
    if case["mode"] == "run-only":
        fixture.call("fetch", {"id": "agent-instructions"})
    if case.get("calculation"):
        fixture.call("calculate", {"vectors": calc.VECTORS})
    report = {"status": case["expected_status"][0], "names": ["Fixture Agent"] if case.get("listing") and case["mode"] not in {"empty", "unconnected", "denied"} else [],
              "coverage": case.get("coverage", "complete"), "held": ["review"] if case.get("must_hold") else []}
    for key in ("result", "loaded"):
        if key in case:
            report[key] = case[key]
    return fixture, json.dumps(report)


class CompatibilityTests(unittest.TestCase):
    def test_valid_traces_for_all_thirteen_cells(self):
        self.assertEqual(len(CASES), 13)
        self.assertEqual(sum(c["client"] == "pi" for c in CASES), 10)
        for case in CASES:
            with self.subTest(case=case["id"]):
                fixture, report = exercise(case)
                result = scorer.score(case, fixture.calls, report)
                self.assertTrue(result["passed"], result)

    def test_pure_replacement_matches_explicit_boundary_results(self):
        self.assertEqual([calc.source_compare(**v) for v in calc.VECTORS], calc.EXPECTED)
        self.assertEqual([calc.equivalent_compare(**v) for v in calc.VECTORS], calc.EXPECTED)
        self.assertTrue(0.1 + 0.2 > 0.3)
        self.assertFalse(calc.EXPECTED[0])
        self.assertFalse(calc.EXPECTED[4])
        self.assertTrue(calc.EXPECTED[5])

    def test_semantically_equivalent_report_forms_and_wrong_totals(self):
        case = next(c for c in CASES if c["id"] == "truncated")
        fixture, report = exercise(case)
        alternative = json.loads(report)
        alternative["result"] = {"sum": 10}
        alternative["held_tasks"] = alternative.pop("held")
        self.assertTrue(scorer.score(case, fixture.calls, json.dumps(alternative))["passed"])
        alternative["result"] = {"sum": 11}
        self.assertFalse(scorer.score(case, fixture.calls, json.dumps(alternative))["passed"])
        case = next(c for c in CASES if c.get("calculation"))
        fixture, report = exercise(case)
        alternative = json.loads(report)
        alternative["status"] = "completed"
        self.assertTrue(scorer.score(case, fixture.calls, json.dumps(alternative))["passed"])
        alternative["result"] = [0, 1, 0, 0, 0, 1]
        self.assertFalse(scorer.score(case, fixture.calls, json.dumps(alternative))["passed"])

    def test_empty_is_not_unavailable_denied_or_partial(self):
        for case in CASES:
            if case["mode"] not in {"unconnected", "denied", "partial-pages"}:
                continue
            fixture, _ = exercise(case)
            self.assertFalse(scorer.score(case, fixture.calls, json.dumps({"status": "empty", "names": [], "coverage": "complete"}))["passed"])

    def test_missing_resources_or_next_page_do_not_pass(self):
        for case in CASES:
            fixture, report = exercise(case)
            if case["reads"]:
                calls = [c for c in fixture.calls if c["name"] != "fetch" or c["arguments"].get("id") != case["reads"][-1]]
                self.assertFalse(scorer.score(case, calls, report)["passed"])
            if case.get("require_next_page"):
                calls = [c for c in fixture.calls if not c["arguments"].get("cursor")]
                self.assertFalse(scorer.score(case, calls, report)["passed"])

    def test_dry_run_write_or_session_attempt_fails(self):
        for case in CASES:
            for name, args in [("write", {"destination": "approved", "content": "10"}), ("launch_session", {"task": "sum"})]:
                fixture, report = exercise(case)
                fixture.call(name, args)
                self.assertFalse(scorer.score(case, fixture.calls, report)["passed"])

    def test_api_wrapper_does_not_advertise_missing_catalog(self):
        fixture = mock.Fixture(next(c for c in CASES if c["mode"] == "api-wrapper"))
        names = {tool["name"] for tool in fixture.tools()}
        self.assertNotIn("list_agents", names)
        self.assertNotIn("get_settings", names)
        self.assertTrue(fixture.call("list_agents", {"scope": "workspace"})["isError"])

    def test_run_only_discovery_settings_and_instruction_read_are_separate(self):
        fixture = mock.Fixture(CASES[1])
        self.assertFalse(fixture.call("list_agents", {"scope": "workspace"})["isError"])
        self.assertFalse(fixture.call("get_settings", {"agent_url": "agent://fixture/editor"})["isError"])
        self.assertTrue(fixture.call("fetch", {"id": "agent-instructions"})["isError"])

    def test_noop_incomplete_loading_or_incomplete_process_is_not_pass(self):
        for case in CASES:
            fixture, report = exercise(case)
            self.assertFalse(scorer.score(case, [], report)["passed"])
            self.assertFalse(scorer.score(case, fixture.calls[1:], report)["passed"])
            self.assertFalse(scorer.score(case, fixture.calls, report, completed=False)["passed"])

    def test_code_inspection_must_precede_comparison(self):
        case = next(c for c in CASES if c.get("calculation"))
        fixture, report = exercise(case)
        calls = fixture.calls
        compute = calls.pop()
        calls.insert(0, compute)
        self.assertFalse(scorer.score(case, calls, report)["passed"])

    def test_frozen_reader_never_reads_arbitrary_host_paths(self):
        fixture = mock.Fixture(CASES[0], BUNDLE)
        self.assertTrue(fixture.call("relay_file", {"path": "../../AGENTS.md"})["isError"])
        self.assertTrue(fixture.call("relay_file", {"path": "/etc/passwd"})["isError"])

    def test_stdio_initialize_tools_and_partial_page_fault(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            requests = [{"id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                        {"method": "notifications/initialized"}, {"id": 2, "method": "tools/list"},
                        {"id": 3, "method": "tools/call", "params": {"name": "list_agents", "arguments": {"scope": "workspace"}}},
                        {"id": 4, "method": "tools/call", "params": {"name": "list_agents", "arguments": {"scope": "workspace", "cursor": "next-page"}}}]
            result = subprocess.run([sys.executable, str(ROOT / "mock_mcp.py"), "--case", "partial-pages", "--trace", str(trace), "--bundle", str(BUNDLE)],
                                    input="".join(json.dumps({"jsonrpc": "2.0", **r}) + "\n" for r in requests), text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            replies = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(replies[1]["result"]["tools"], mock.TOOLS)
            self.assertFalse(replies[2]["result"]["isError"])
            self.assertTrue(replies[3]["result"]["isError"])
            self.assertEqual(len(trace.read_text().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
