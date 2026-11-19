import ast
import copy
import functools
import importlib.util
from pathlib import Path
import re
import unittest

TESTS = Path(__file__).resolve().parent
SUITES = {
    "compatibility": "test_compatibility",
    "security": "test_security_fixture",
    "write-lifecycle": "test_write_lifecycle",
    "resume-handoff": "test_resume_handoff_fixture",
    "response-language": "test_response_language_scoring",
}
CHECK_PATTERNS = (r"\berrors\.append\(", r"^[ \t]*raise\b(?![ \t]+SystemExit)", r"\breturn False\b")


@functools.cache
def rows_of(module_name):
    spec = importlib.util.spec_from_file_location("rules_" + module_name, TESTS / f"{module_name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ONE_FAULT_ROWS


def is_check(node):
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        func = node.value.func
        return (isinstance(func, ast.Attribute) and func.attr == "append"
                and isinstance(func.value, ast.Name) and func.value.id == "errors")
    if isinstance(node, ast.Raise):
        raised = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
        return not (isinstance(raised, ast.Name) and raised.id == "SystemExit")
    return isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is False


class Disable(ast.NodeTransformer):
    def __init__(self, position):
        self.position = position

    def replace(self, node):
        if (node.lineno, node.col_offset) != self.position:
            return node
        if isinstance(node, ast.Return):
            return ast.copy_location(ast.Return(ast.Constant(True)), node)
        return ast.copy_location(ast.Pass(), node)

    visit_Expr = visit_Raise = visit_Return = replace


def scorer(path, position=None):
    tree = ast.parse(path.read_text())
    if position is not None:
        tree = ast.fix_missing_locations(Disable(position).visit(tree))
    namespace = {"__name__": "scorer_under_test", "__file__": str(path)}
    exec(compile(tree, str(path), "exec"), namespace)
    return namespace["score"]


def outcome(score, row):
    _, args, kwargs, _ = row
    try:
        return score(*copy.deepcopy(args), **copy.deepcopy(kwargs))["errors"]
    except Exception as error:
        return f"raised {type(error).__name__}: {error}"


class ScorerRuleTests(unittest.TestCase):
    def test_each_row_reports_exactly_its_expected_errors(self):
        for suite, module in SUITES.items():
            score = scorer(TESTS / suite / "score.py")
            rows = rows_of(module)
            with self.subTest(suite=suite):
                self.assertTrue(rows, f"{suite} has no ONE_FAULT_ROWS")
            for row in rows:
                with self.subTest(suite=suite, row=row[0]):
                    self.assertEqual(outcome(score, row), row[3])

    def test_disabling_any_scorer_check_changes_some_row(self):
        for suite, module in SUITES.items():
            with self.subTest(suite=suite):
                path = TESTS / suite / "score.py"
                source = path.read_text()
                positions = sorted((node.lineno, node.col_offset) for node in ast.walk(ast.parse(source)) if is_check(node))
                counted = sum(len(re.findall(pattern, source, re.MULTILINE)) for pattern in CHECK_PATTERNS)
                self.assertEqual(len(positions), counted, f"{suite}: AST found {len(positions)} checks, text has {counted}")
                self.assertTrue(positions, f"{suite}: no checks found")
                lines = source.splitlines()
                survivors = []
                for line, column in positions:
                    mutant = scorer(path, (line, column))
                    if all(outcome(mutant, row) == row[3] for row in rows_of(module)):
                        survivors.append(f"{suite}/score.py:{line}: {lines[line - 1].strip()}")
                self.assertEqual(survivors, [], "checks no row notices when disabled:\n" + "\n".join(survivors))


if __name__ == "__main__":
    unittest.main()
