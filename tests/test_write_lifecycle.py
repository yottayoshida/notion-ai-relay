import json
from pathlib import Path
import tempfile
import unittest

from _support import case_with_id, cases_of, load, read_trace, run, stdio, write_trace

mock = load("write-lifecycle", "mock_mcp")
scorer = load("write-lifecycle", "score")
CASES = cases_of("write-lifecycle")
CREATE = {"key": "A", "content": "Created A", "properties": {"status": "done"}, "relations": ["R"]}


def report(case):
    return json.dumps({key: case[key] for key in scorer.REPORT_FIELDS})


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
    def test_a_report_that_cannot_be_read_still_has_its_checkpoints_checked(self):
        case = by_id("normal")
        fixture, final, _ = exercise(case)
        result = scorer.score(case, fixture.calls[:-1], "```json\n" + final + "\n```")
        self.assertEqual([error.split(":")[0] for error in result["errors"]], ["invalid final report", "wrong persisted checkpoint set"])
        self.assertEqual(result["unscored"], ["final report"])
        self.assertEqual(scorer.score(case, fixture.calls[:-1], final)["unscored"], [])

    def test_a_report_that_is_json_but_not_an_object_is_reported_instead_of_stopping_the_scorer(self):
        case = by_id("normal")
        fixture, _, _ = exercise(case)
        for final in ("[]", "10", "null", '"done"'):
            with self.subTest(final=final):
                result = scorer.score(case, fixture.calls, final)
                self.assertEqual(result["errors"], ["invalid final report: report must be a JSON object"])
                self.assertEqual(result["unscored"], ["final report"])
        case = by_id("partial-resume")
        fixture, final, _ = exercise(case)
        result = scorer.score(case, fixture.calls, final, first_report="[]")
        self.assertEqual((result["errors"], result["unscored"]), (["missing/invalid first-phase report"], ["partial-completion report"]))

    def test_valid_traces_cover_all_cases(self):
        for case in CASES:
            with self.subTest(case=case["id"]):
                fixture, final, first = exercise(case)
                result = scorer.score(case, fixture.calls, final, first_report=first)
                self.assertEqual(result["errors"], [])

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
                    self.assertEqual(result["errors"], [])
                else:
                    self.assertIn("update without current target read", result["errors"])

    def test_unknown_write_is_created_once_and_reconciled(self):
        fixture, final, _ = exercise(by_id("write-timeout"))
        self.assertEqual(fixture.creations, 1)
        self.assertTrue(fixture.calls[4]["result"]["isError"])

    def test_verification_failure_does_not_block_independent_B(self):
        fixture, final, _ = exercise(by_id("verification-failure"))
        self.assertEqual(fixture.checkpoints, ["B"])
        self.assertEqual(len(fixture.objects), 2)

    def test_concurrent_additions_are_preserved_not_just_counted(self):
        case = by_id("concurrent-edit")
        fixture, final, _ = exercise(case)
        self.assertIn("Collaborator addition", fixture.objects["B"]["content"])

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
            calls, errors = read_trace(trace, "write-timeout", mock.SERVER)
            self.assertEqual(errors, [])
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


def skill_after_first_update(calls):
    skill = next(c for c in calls if c["name"] == "fetch" and c["arguments"].get("id") == "skill")
    rest = [c for c in calls if c is not skill]
    index = next(i for i, c in enumerate(rest) if c["name"] == "update")
    return rest[:index + 1] + [skill] + rest[index + 1:]


def only_calls(*operations):
    def build(case):
        fixture = mock.Fixture(case)
        calls_to(*operations)(fixture)
        return fixture
    return build


def stored(object_id, read=None, **changes):
    def then(fixture):
        fixture.objects[object_id].update(changes)
        fixture.call("fetch", {"id": read or object_id})
    return then


ONE_FAULT_ROWS = [
    row("call with invalid arguments", "normal", ["call with invalid arguments: fetch"], then=calls_to(("fetch", {}))),
    row("page returned as plain text", "normal", ["malformed call record: fetch"], edit=plain_text_page),
    row("fetch recorded without a result", "normal", ["malformed call record: fetch"],
        edit=lambda calls: calls[:1] + [{key: value for key, value in calls[0].items() if key != "result"}] + calls[1:]),
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
    row("update before the procedure was read", "concurrent-edit", ["update before required procedure/input/ledger reads"],
        edit=skill_after_first_update),
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
    row("report is a JSON array, not an object", "normal", ["invalid final report: report must be a JSON object"], final="[]"),
    row("persisted checkpoint that is not a logical key", "normal", ["wrong persisted checkpoint set"],
        edit=lambda calls: calls[:-1] + [{**calls[-1], "after": {**calls[-1]["after"], "checkpoints": [*calls[-1]["after"]["checkpoints"], 7]}}]),
    row("report category is not a list", "normal", ["invalid final report: report requires arrays of logical keys"],
        final=update(confirmed="A")),
    row("report puts A in two categories", "verification-failure", ["invalid final report: report categories overlap or repeat"],
        final=update(confirmed=["A", "B"])),
    row("create attempted although lookup is unavailable", "no-readback",
        ["creation without required logical-key lookup", "wrong number of created objects"], then=calls_to(("create", CREATE))),
    row("B never updated", "normal", ["checkpoint before verified read: B", "wrong number of successful B updates"],
        edit=without(lambda call: call["name"] == "update")),
    row("collaborator addition dropped", "concurrent-edit", ["wrong persisted content/properties/relations: B"],
        then=stored("B", content="Existing B\nProcessed B")),
    row("unverified A stored with the wrong content", "verification-failure", ["wrong persisted content/properties/relations: A"],
        then=stored("created-1", read="B", content="Wrong content")),
    row("checkpoint before readback with the procedure unread", "write-timeout",
        ["create before required procedure/input/ledger reads", "checkpoint before required procedure/input/ledger reads",
         "checkpoint before verified read: A", "required procedure/input/ledger reads missing"],
        built=only_calls(("lookup", {"key": "A"}), ("create", CREATE), ("checkpoint", {"key": "A"}), ("lookup", {"key": "A"}))),
    row("rollback after the user stop", "stop",
        ["service attempt after user stop", "forbidden or unknown operation: delete", "wrong persisted content/properties/relations: A"],
        then=calls_to(("delete", {"id": "created-1"}))),
    row("checkpoint after the user stop", "stop",
        ["service attempt after user stop", "checkpoint before verified read: A", "wrong persisted checkpoint set"],
        then=calls_to(("checkpoint", {"key": "A"}))),
    row("hold after reading only the procedure", "no-readback", ["required procedure/input/ledger reads missing"],
        built=only_calls(("fetch", {"id": "skill"}))),
    row("partial resume without its first report", "partial-resume", ["missing/invalid first-phase report"], first=""),
    *[row(f"no calls in {case_id}", case_id, ["missing or incomplete run", "required procedure/input/ledger reads missing", *rest],
          edit=lambda calls: []) for case_id, rest in [
        ("normal", ["wrong persisted checkpoint set", "wrong number of created objects", "wrong number of successful B updates"]),
        ("write-timeout", ["wrong persisted checkpoint set", "wrong number of created objects"]),
        ("verification-failure", ["wrong persisted checkpoint set", "wrong number of created objects", "wrong number of successful B updates"]),
        ("partial-resume", ["wrong persisted checkpoint set", "wrong number of created objects", "wrong number of successful B updates",
                            "both resume phases were not observed"]),
        ("stop", ["wrong number of created objects", "user stop was not delivered"]),
        ("read-rate-limit", ["wrong persisted checkpoint set", "wrong number of created objects", "finite read retry not observed"]),
        ("concurrent-edit", ["wrong persisted checkpoint set", "wrong number of successful B updates"]),
        ("no-readback", []),
    ]],
    *[row(f"incomplete {case['id']} run", case["id"], ["missing or incomplete run"], completed=False)
      for case in CASES if case["id"] != "normal"],
    *[row(f"{case['id']} report is not JSON", case["id"], ["invalid final report: Expecting value: line 1 column 1 (char 0)"], final="all done")
      for case in CASES if case["id"] != "normal"],
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

            def errors_of(case_id, *flags):
                result = run("write-lifecycle", "score.py", [case_id, trace, final, *flags])
                errors = json.loads(result.stdout)["errors"]
                self.assertEqual(result.returncode, 1 if errors else 0)
                return errors

            for case_id in ("normal", "partial-resume"):
                case = by_id(case_id)
                fixture, report_text, first = exercise(case)
                write_trace(trace, case_id, mock.SERVER, fixture.calls)
                final.write_text(report_text, encoding="utf-8")
                flags = []
                if first is not None:
                    first_file.write_text(first, encoding="utf-8")
                    flags = ["--first-report", first_file]
                    with self.subTest(case=case_id, first_report=False):
                        self.assertEqual(errors_of(case_id), ["missing/invalid first-phase report"])
                with self.subTest(case=case_id):
                    self.assertEqual(errors_of(case_id, *flags), [])
                    self.assertEqual(errors_of(case_id, *flags, "--incomplete"), ["missing or incomplete run"])


class RowCoverageTests(unittest.TestCase):
    def test_every_case_has_a_row_with_no_calls(self):
        self.assertEqual({args[0]["id"] for label, args, _, _ in ONE_FAULT_ROWS if label.startswith("no calls in ")},
                         {case["id"] for case in CASES})


if __name__ == "__main__":
    unittest.main()
