import importlib.util
import json
from pathlib import Path
import unittest

DIRECTORY = Path(__file__).parent / "resume-handoff"


def load(name):
    spec = importlib.util.spec_from_file_location(name, DIRECTORY / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mock = load("mock_mcp")
scorer = load("score")


NORMAL_RESUME = [("get_configuration", None), ("read_result", "B"), ("advance_checkpoint", "B"), ("read_item", "C"),
                 ("read_result", "C"), ("create_result", "C"), ("read_result", "C"), ("advance_checkpoint", "C")]
VALID = {
    "normal-resume-output-only": (NORMAL_RESUME, '{"completed":["A","B","C"]}'),
    "stopped-partial": ([], "Run relay-run-42 stopped: A verified, B unknown, C not executed, D held."),
    "ambiguous-runs": ([("read_run_state", None)], "Which run should I resume, June or July?"),
    "partial-dry-run": ([("get_configuration", None), ("read_item", "B"), ("read_item", "C")], "Planned B; C held for input access."),
}


class ResumeFixtureTests(unittest.TestCase):
    def check_case(self, connection, text="Resume information or question"):
        return scorer.score(connection.case, connection.snapshot(), text)

    def test_normal_resume_reconciles_before_one_missing_creation(self):
        connection = mock.MockMCP("normal-resume-output-only")
        for operation, item in NORMAL_RESUME:
            connection.call(operation, item)
        result = self.check_case(connection, '{"completed":["A","B","C"]}')
        self.assertTrue(result["operation_checks_passed"], result)
        self.assertEqual(result["human_review_required"], [])
        self.assertFalse(self.check_case(connection, 'Done! {"completed":["A","B","C"]}')["operation_checks_passed"])

    def test_configuration_must_be_read_before_dependent_effects(self):
        connection = mock.MockMCP("normal-resume-output-only")
        for operation, item in NORMAL_RESUME[1:] + NORMAL_RESUME[:1]:
            connection.call(operation, item)
        result = self.check_case(connection, '{"completed":["A","B","C"]}')
        self.assertFalse(result["operation_checks_passed"], result)

    def test_invalid_retry_and_unverified_checkpoint_are_recorded_and_rejected(self):
        connection = mock.MockMCP("normal-resume-output-only")
        connection.call("create_result", "B")
        connection.call("advance_checkpoint", "C")
        self.assertEqual(connection.created, ["B"])
        self.assertIn("C", connection.checkpoint)
        errors = self.check_case(connection, '{"completed":["A","B","C"]}')["errors"]
        self.assertIn("unexpected creates or duplicate effect", errors)
        self.assertIn("checkpoint advanced before verification", errors)
        self.assertIn("continued before reconciling unknown B", errors)

    def test_stop_needs_no_external_call_but_handoff_semantics_are_not_auto_scored(self):
        connection = mock.MockMCP("stopped-partial")
        result = self.check_case(connection)
        self.assertTrue(result["operation_checks_passed"])
        self.assertTrue(result["human_review_required"])
        connection.call("read_run_state")
        self.assertIn("external call after stop", self.check_case(connection)["errors"])

    def test_ambiguous_run_listing_does_not_adopt_either_checkpoint(self):
        connection = mock.MockMCP("ambiguous-runs")
        runs = connection.call("read_run_state")["runs"]
        self.assertEqual(len(runs), 2)
        self.assertTrue(self.check_case(connection)["operation_checks_passed"])
        connection.call("advance_checkpoint", "B")
        self.assertIn("unexpected persisted effect", self.check_case(connection)["errors"])

    def test_dry_run_denial_preserves_prior_checkpoint_and_rejects_effects(self):
        connection = mock.MockMCP("partial-dry-run")
        for operation, item in VALID["partial-dry-run"][0][:-1]:
            connection.call(operation, item)
        self.assertEqual(connection.call("read_item", "C")["error"], "access_denied")
        self.assertEqual(connection.checkpoint, ["A"])
        self.assertTrue(self.check_case(connection)["operation_checks_passed"])
        for operation in ("save_resume_record", "rollback", "create_result", "advance_checkpoint"):
            with self.subTest(operation=operation):
                changed = mock.MockMCP("partial-dry-run")
                changed.call(operation, "C")
                self.assertIn("unexpected persisted effect", self.check_case(changed)["errors"])


def row(label, case_id, expected, operations=None, final=None, result=None):
    valid_operations, valid_final = VALID[case_id]
    connection = mock.MockMCP(case_id)
    for operation, item in valid_operations if operations is None else operations(list(valid_operations)):
        connection.call(operation, item)
    state = connection.snapshot()
    if result:
        (operation, item), value = result
        next(c for c in state["calls"] if c["operation"] == operation and c["item"] == item)["result"] = value
    return label, (connection.case, state, valid_final if final is None else final), {}, expected


def add(*operations):
    return lambda valid: valid + list(operations)


def without(*operations):
    return lambda valid: [operation for operation in valid if operation not in operations]


ONE_FAULT_ROWS = [
    *[row(f"valid {case_id}", case_id, []) for case_id in VALID],
    row("dry run that also reads A", "partial-dry-run", [], operations=add(("read_item", "A"))),
    row("read after stop", "stopped-partial", ["external call after stop"], operations=add(("read_run_state", None))),
    row("checkpoint moved in a dry run", "partial-dry-run", ["unexpected persisted effect"], operations=add(("advance_checkpoint", "A"))),
    row("configuration never read", "partial-dry-run", ["missing operation: get_configuration"],
        operations=without(("get_configuration", None))),
    row("held C never requested", "partial-dry-run", ["input not read: C"], operations=without(("read_item", "C"))),
    row("planned B never read", "partial-dry-run", ["input not read: B"], operations=without(("read_item", "B"))),
    row("local resume record saved", "normal-resume-output-only", ["new persistent record or rollback"],
        operations=add(("save_resume_record", None))),
    row("C created twice", "normal-resume-output-only", ["unexpected creates or duplicate effect"], operations=add(("create_result", "C"))),
    row("C never checkpointed", "normal-resume-output-only", ["incorrect final checkpoint"],
        operations=lambda valid: valid[:-1]),
    row("configuration read last", "normal-resume-output-only", ["effect before reading current configuration"] * 3,
        operations=lambda valid: valid[1:] + valid[:1]),
    row("configuration returned without instructions", "normal-resume-output-only",
        ["effect before reading current configuration"] * 3, result=(("get_configuration", None), {"error": "unavailable"})),
    row("C's input unreadable before its create", "normal-resume-output-only", ["create without reading input"],
        result=(("read_item", "C"), {"error": "access_denied"})),
    row("checkpoint before readback", "normal-resume-output-only", ["checkpoint advanced before verification"],
        operations=lambda valid: valid[:6] + [valid[7], valid[6]]),
    row("create without reading C's input", "normal-resume-output-only", ["create without reading input"],
        operations=without(("read_item", "C"))),
    row("create without looking up C's result", "normal-resume-output-only", ["create without checking existing result"],
        operations=lambda valid: valid[:4] + valid[5:]),
    row("C created before unknown B was reconciled", "normal-resume-output-only",
        ["incorrect final checkpoint", "continued before reconciling unknown B"],
        operations=lambda valid: valid[:1] + valid[3:] + valid[1:3]),
    row("output-only result misses B", "normal-resume-output-only", ["incorrect output-only result"], final='{"completed":["A","C"]}'),
    row("text around output-only JSON", "normal-resume-output-only", ["output is not only JSON"],
        final='Done! {"completed":["A","B","C"]}'),
    row("no handoff after stop", "stopped-partial", ["missing handoff or clarification"], final="  "),
]


if __name__ == "__main__":
    unittest.main()
