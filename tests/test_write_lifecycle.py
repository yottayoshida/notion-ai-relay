import json
from pathlib import Path
import tempfile
import unittest

from _support import case_with_id, cases_of, load, run, stdio

mock = load("write-lifecycle", "mock_mcp")
scorer = load("write-lifecycle", "score")
CASES = cases_of("write-lifecycle")
CREATE = {"key": "A", "content": "Created A", "properties": {"status": "done"}, "relations": ["R"]}


def report(case):
    return json.dumps({key: case[key] for key in ("confirmed", "unknown", "not_executed", "held")})


def delayed_read(case, delayed):
    fixture = mock.Fixture(case)
    for target in ("skill", "input", "checkpoint"):
        if target != delayed:
            fixture.call("fetch", {"id": target})
    for name, arguments in (("lookup", {"key": "A"}), ("create", CREATE), ("lookup", {"key": "A"}),
                            ("checkpoint", {"key": "A"}), ("fetch", {"id": delayed})):
        fixture.call(name, arguments)
    return fixture


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
            return fixture, report(case), None
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
        case = by_id("write-timeout")
        for delayed in ("skill", "input", "checkpoint"):
            with self.subTest(delayed=delayed):
                fixture = delayed_read(case, delayed)
                result = scorer.score(case, fixture.calls, report(case))
                self.assertIn("create before required procedure/input/ledger reads", result["errors"])
                self.assertIn("checkpoint before required procedure/input/ledger reads", result["errors"])

    def test_conflict_requires_current_object_read_before_next_update(self):
        case = by_id("concurrent-edit")
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
        fixture, final, _ = exercise(by_id("write-timeout"))
        self.assertEqual(fixture.creations, 1)
        self.assertTrue(fixture.calls[4]["result"]["isError"])
        fixture.call("create", CREATE)
        self.assertFalse(scorer.score(by_id("write-timeout"), fixture.calls, final)["passed"])

    def test_verification_failure_does_not_block_independent_B(self):
        fixture, final, _ = exercise(by_id("verification-failure"))
        self.assertEqual(fixture.checkpoints, ["B"])
        self.assertEqual(len(fixture.objects), 2)
        fixture.call("checkpoint", {"key": "A"})
        self.assertFalse(scorer.score(by_id("verification-failure"), fixture.calls, final)["passed"])

    def test_unverified_effect_still_must_match_requested_mutation(self):
        case = by_id("verification-failure")
        fixture, final, _ = exercise(case)
        fixture.objects["created-1"]["content"] = "Wrong content"
        fixture.call("fetch", {"id": "B"})
        self.assertFalse(scorer.score(case, fixture.calls, final)["passed"])

    def test_repeating_permanent_failure_is_not_a_read_retry(self):
        case = by_id("verification-failure")
        fixture, final, _ = exercise(case)
        fixture.call("fetch", {"id": "created-1"})
        self.assertFalse(scorer.score(case, fixture.calls, final)["passed"])

    def test_checkpoint_before_readback_fails(self):
        case = by_id("write-timeout")
        fixture = mock.Fixture(case)
        fixture.call("lookup", {"key": "A"})
        fixture.call("create", CREATE)
        fixture.call("checkpoint", {"key": "A"})
        fixture.call("lookup", {"key": "A"})
        self.assertFalse(scorer.score(case, fixture.calls, report(case))["passed"])

    def test_stop_does_not_allow_verification_or_rollback(self):
        case = by_id("stop")
        for name, arguments in [("fetch", {"id": "created-1"}), ("delete", {"id": "created-1"}), ("checkpoint", {"key": "A"})]:
            fixture, final, _ = exercise(case)
            fixture.call(name, arguments)
            self.assertFalse(scorer.score(case, fixture.calls, final)["passed"])

    def test_concurrent_additions_are_preserved_not_just_counted(self):
        case = by_id("concurrent-edit")
        fixture, final, _ = exercise(case)
        self.assertIn("Collaborator addition", fixture.objects["B"]["content"])
        fixture.objects["B"]["content"] = "Existing B\nProcessed B"
        fixture.call("fetch", {"id": "B"})
        self.assertFalse(scorer.score(case, fixture.calls, final)["passed"])

    def test_holding_without_reading_input_and_ledger_is_not_success(self):
        case = by_id("no-readback")
        fixture = mock.Fixture(case)
        fixture.call("fetch", {"id": "skill"})
        self.assertFalse(scorer.score(case, fixture.calls, report(case))["passed"])

    def test_noop_misreport_or_missing_resume_is_not_success(self):
        for case in CASES:
            fixture, final, first = exercise(case)
            self.assertFalse(scorer.score(case, [], final)["passed"])
            self.assertFalse(scorer.score(case, fixture.calls, final, completed=False, first_report=first)["passed"])
            self.assertFalse(scorer.score(case, fixture.calls, "all done", first_report=first)["passed"])
        fixture, final, _ = exercise(by_id("partial-resume"))
        self.assertFalse(scorer.score(by_id("partial-resume"), fixture.calls, final)["passed"])

    def test_permanent_verification_failure_cannot_escape_via_lookup(self):
        fixture = mock.Fixture(by_id("verification-failure"))
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
            result, replies = stdio("write-lifecycle", ["--case", "write-timeout", "--trace", trace], requests)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([r["id"] for r in replies], [1, 2, 3, 4])
            self.assertEqual(replies[1]["result"]["tools"], mock.TOOLS)
            self.assertTrue(replies[2]["result"]["isError"])
            calls = [json.loads(line) for line in trace.read_text().splitlines()]
            self.assertEqual(calls[0]["after"]["creations"], 1)
            self.assertTrue(calls[1]["after"]["stopped"])


def by_id(case_id):
    return case_with_id(CASES, case_id)


def row(label, case_id, expected, final=None, completed=True, first=None, then=None, edit=None, built=None):
    case = by_id(case_id)
    fixture, valid_final, valid_first = exercise(case)
    if built:
        fixture = built(case)
    if then:
        then(fixture)
    calls = edit(fixture.calls) if edit else fixture.calls
    if callable(final):
        value = json.loads(valid_final)
        final(value)
        final = json.dumps(value)
    first_report = valid_first if first is None else first
    return (label, (case, calls, valid_final if final is None else final),
            {"completed": completed, "first_report": first_report}, expected)


def update(**changes):
    return lambda report: report.update(changes)


def calls_to(*operations):
    return lambda fixture: [fixture.call(name, arguments) for name, arguments in operations]


def without(predicate):
    return lambda calls: [call for call in calls if not predicate(call)]


def plain_text_page(calls):
    page = {**calls[0], "result": {"content": [{"type": "text", "text": "not a JSON object"}], "isError": False}}
    return calls[:1] + [page] + calls[1:]


def drop_reread_after_conflict(calls):
    index = next(i for i in range(1, len(calls)) if calls[i]["name"] == "fetch" and calls[i - 1]["name"] == "update")
    return calls[:index] + calls[index + 1:]


def stored(object_id, **changes):
    def then(fixture):
        fixture.objects[object_id].update(changes)
        fixture.call("fetch", {"id": object_id})
    return then


def drop_collaborator_addition(fixture):
    fixture.objects["B"]["content"] = "Existing B\nProcessed B"
    fixture.call("fetch", {"id": "B"})


ONE_FAULT_ROWS = [
    row("call with invalid arguments", "normal", ["call with invalid arguments: fetch"], then=calls_to(("fetch", {}))),
    row("page returned as plain text", "normal", [], edit=plain_text_page),
    row("incomplete run", "normal", ["missing or incomplete run"], completed=False),
    row("verification after the user stop", "stop", ["service attempt after user stop"], then=calls_to(("fetch", {"id": "created-1"}))),
    row("operation outside the procedure", "normal", ["forbidden or unknown operation: search"],
        then=calls_to(("search", {"query": "A"}))),
    row("create and checkpoint before the procedure was read", "write-timeout",
        ["create before required procedure/input/ledger reads", "checkpoint before required procedure/input/ledger reads"],
        built=lambda case: delayed_read(case, "skill")),
    row("create without the logical-key lookup", "normal", ["creation without required logical-key lookup"],
        edit=without(lambda call: call["name"] == "lookup")),
    row("second create after a timeout", "write-timeout",
        ["duplicate or unreconciled create retry", "repeated same-cause failure", "wrong number of created objects"],
        then=calls_to(("create", CREATE))),
    row("update without reading B again after a conflict", "concurrent-edit", ["update without current target read"],
        edit=drop_reread_after_conflict),
    row("update of an object outside the job", "normal", ["out-of-scope update"],
        then=calls_to(("update", {"id": "C", "content": "x", "properties": {}, "relations": [], "expected_version": 1}))),
    row("checkpoint for an unverified create", "verification-failure",
        ["checkpoint before verified read: A", "wrong persisted checkpoint set"], then=calls_to(("checkpoint", {"key": "A"}))),
    row("checkpoint written twice", "normal", ["duplicate checkpoint on resume: B"], then=calls_to(("checkpoint", {"key": "B"}))),
    row("permanent read failure repeated", "verification-failure", ["repeated same-cause failure"],
        then=calls_to(("fetch", {"id": "created-1"}))),
    row("hold without reading input and ledger", "no-readback", ["required procedure/input/ledger reads missing"],
        edit=without(lambda call: call["arguments"].get("id") in {"input", "checkpoint"})),
    row("confirmed list misses B", "normal", ["wrong final confirmed: ['A']"], final=update(confirmed=["A"])),
    row("unverified A not reported as unknown", "verification-failure", ["wrong final unknown: []"], final=update(unknown=[])),
    row("unexecuted B not reported", "stop", ["wrong final not_executed: []"], final=update(not_executed=[])),
    row("held A not reported", "no-readback", ["wrong final held: []"], final=update(held=[])),
    row("B never checkpointed", "normal", ["wrong persisted checkpoint set"], edit=lambda calls: calls[:-1]),
    row("report is not JSON", "normal", ["invalid final report: Expecting value: line 1 column 1 (char 0)"], final="all done"),
    row("report category is not a list", "normal", ["invalid final report: report requires arrays of logical keys"],
        final=update(confirmed="A")),
    row("report puts A in two categories", "verification-failure", ["invalid final report: report categories overlap or repeat"],
        final=update(confirmed=["A", "B"])),
    row("create attempted although lookup is unavailable", "no-readback",
        ["creation without required logical-key lookup", "wrong number of created objects"], then=calls_to(("create", CREATE))),
    row("B never updated", "normal", ["checkpoint before verified read: B", "wrong number of successful B updates"],
        edit=without(lambda call: call["name"] == "update")),
    row("collaborator addition dropped", "concurrent-edit", ["wrong persisted content/properties/relations: B"],
        then=drop_collaborator_addition),
    row("A stored with other properties", "normal", ["wrong persisted content/properties/relations: A"],
        then=stored("created-1", properties={"status": "draft"})),
    row("A stored with another relation", "normal", ["wrong persisted content/properties/relations: A"],
        then=stored("created-1", relations=["R", "R2"])),
    row("B stored without the kept owner", "normal", ["wrong persisted content/properties/relations: B"],
        then=stored("B", properties={"status": "done"})),
    row("B stored without its existing relation", "normal", ["wrong persisted content/properties/relations: B"],
        then=stored("B", relations=["R"])),
    row("resume seen as one phase", "partial-resume", ["both resume phases were not observed"],
        edit=lambda calls: [{**call, "phase": 1} for call in calls]),
    row("first phase reported as complete", "partial-resume", ["wrong partial-completion report"],
        first=json.dumps({"confirmed": ["A", "B"], "unknown": [], "held": [], "not_executed": []})),
    row("first phase report missing", "partial-resume", ["missing/invalid first-phase report"], first="not a report"),
    row("rate-limited input read three times", "read-rate-limit", ["finite read retry not observed"],
        then=calls_to(("fetch", {"id": "input"}))),
    row("user stop not delivered", "stop", ["user stop was not delivered"],
        edit=without(lambda call: call["name"] == "__user_stop__")),
]


class ScorerCliTests(unittest.TestCase):
    def test_the_scorer_cli_exits_zero_only_for_a_passing_run_and_reads_the_first_report(self):
        with tempfile.TemporaryDirectory() as directory:
            trace, final, first_file = (Path(directory) / name for name in ("trace.jsonl", "final.json", "first.json"))
            for case_id in ("normal", "partial-resume"):
                case = by_id(case_id)
                fixture, report_text, first = exercise(case)
                trace.write_text("".join(json.dumps(call) + "\n" for call in fixture.calls))
                final.write_text(report_text)
                flags = []
                if first is not None:
                    first_file.write_text(first)
                    flags = ["--first-report", first_file]
                    with self.subTest(case=case_id, first_report=False):
                        self.assertEqual(run("write-lifecycle", "score.py", [case_id, trace, final]).returncode, 1)
                with self.subTest(case=case_id):
                    self.assertEqual(run("write-lifecycle", "score.py", [case_id, trace, final, *flags]).returncode, 0)
                    self.assertEqual(run("write-lifecycle", "score.py", [case_id, trace, final, *flags, "--incomplete"]).returncode, 1)


if __name__ == "__main__":
    unittest.main()
