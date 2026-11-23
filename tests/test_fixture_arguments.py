import json
from pathlib import Path
import tempfile
import unittest

from _mcp_fixture import TYPES, schema_error
from _support import TESTS, case_with_id, cases_of, load, read_trace, stdio

SUITES = {
    "security": ("authorized-normal", [], [
        ("missing", "notion_fetch", {}, "invalid_arguments"),
        ("unexpected", "notion_fetch", {"id": "skill", "page": 2}, "invalid_arguments"),
        ("wrong type", "notion_fetch", {"id": {}}, "invalid_arguments"),
        ("wrong item type", "file_urls", {"references": [7]}, "invalid_arguments"),
    ]),
    "compatibility": ("comparison-code", ["--bundle", TESTS.parent], [
        ("missing", "list_agents", {}, "invalid_arguments"),
        ("unexpected", "list_agents", {"scope": "workspace", "page": 2}, "invalid_arguments"),
        ("wrong type", "list_agents", {"scope": 5}, "invalid_arguments"),
        ("missing nested", "calculate", {"vectors": [{"amounts": ["1"], "threshold": "0", "label": "x"}]}, "invalid_arguments"),
        ("cannot process", "calculate", {"vectors": [{"amounts": ["one"], "threshold": "0", "label": "x", "expected_label": "x"}]},
         "fixture_error"),
    ]),
    "write-lifecycle": ("normal", [], [
        ("missing", "fetch", {}, "invalid_arguments"),
        ("unexpected", "fetch", {"id": "B", "page": 2}, "invalid_arguments"),
        ("wrong type", "update", {"id": "B", "content": "Existing B", "properties": {"status": "done"}, "relations": "R"},
         "invalid_arguments"),
        ("wrong value type", "create", {"key": "A", "content": "x", "properties": {"status": 1}, "relations": ["R"]},
         "invalid_arguments"),
    ]),
}
SCHEMA_KEYWORDS = {"type", "description", "properties", "required", "additionalProperties", "items", "enum", "minimum", "maximum"}


def schemas(schema):
    yield schema
    for item in schema.get("properties", {}).values():
        yield from schemas(item)
    for key in ("items", "additionalProperties"):
        if isinstance(schema.get(key), dict):
            yield from schemas(schema[key])


class FixtureArgumentTests(unittest.TestCase):
    def test_calls_the_fixture_cannot_process_get_tool_errors_are_recorded_and_the_server_keeps_running(self):
        for suite, (case_id, arguments, bad_calls) in SUITES.items():
            with self.subTest(suite=suite), tempfile.TemporaryDirectory() as directory:
                trace = Path(directory) / "trace.jsonl"
                requests = [{"id": index, "method": "tools/call", "params": {"name": name, "arguments": call_arguments}}
                            for index, (_, name, call_arguments, _) in enumerate(bad_calls, 1)]
                result, replies = stdio(suite, ["--case", case_id, "--trace", trace, *arguments],
                                        requests + [{"id": len(bad_calls) + 1, "method": "ping"}])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual([reply["id"] for reply in replies], list(range(1, len(bad_calls) + 2)))
                for (label, _, _, error), reply in zip(bad_calls, replies):
                    with self.subTest(suite=suite, call=label):
                        self.assertTrue(reply["result"]["isError"])
                        self.assertEqual(json.loads(reply["result"]["content"][0]["text"])["error"], error)
                recorded, errors = read_trace(trace, case_id, load(suite, "mock_mcp").SERVER)
                self.assertEqual(errors, [])
                self.assertEqual([(call["name"], call["arguments"]) for call in recorded],
                                 [(name, call_arguments) for _, name, call_arguments, _ in bad_calls])
                outcome = load(suite, "score").score(case_with_id(cases_of(suite), case_id), recorded, "")
                self.assertFalse(outcome["passed"])
                for _, name, _, error in bad_calls:
                    if error == "invalid_arguments":
                        self.assertIn(f"call with invalid arguments: {name}", outcome["errors"])

    def test_traces_are_ascii_whatever_the_arguments_contain(self):
        for suite, (case_id, arguments, bad_calls) in SUITES.items():
            name = bad_calls[0][1]
            key = next(tool for tool in load(suite, "mock_mcp").TOOLS if tool["name"] == name)["inputSchema"]["required"][0]
            with self.subTest(suite=suite), tempfile.TemporaryDirectory() as directory:
                trace = Path(directory) / "trace.jsonl"
                result, replies = stdio(suite, ["--case", case_id, "--trace", trace, *arguments],
                                        [{"id": 1, "method": "tools/call", "params": {"name": name, "arguments": {key: "報告 → 10"}}},
                                         {"id": 2, "method": "ping"}])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual([reply["id"] for reply in replies], [1, 2])
                self.assertTrue(trace.read_bytes().isascii())
                recorded, errors = read_trace(trace, case_id, load(suite, "mock_mcp").SERVER)
                self.assertEqual((errors, recorded[0]["arguments"]), ([], {key: "報告 → 10"}))

    def test_a_tools_call_without_a_string_name_gets_a_tool_error_and_the_server_keeps_running(self):
        for suite, (case_id, arguments, _) in SUITES.items():
            with self.subTest(suite=suite), tempfile.TemporaryDirectory() as directory:
                trace = Path(directory) / "trace.jsonl"
                result, replies = stdio(suite, ["--case", case_id, "--trace", trace, *arguments],
                                        [{"id": 1, "method": "tools/call", "params": {"name": {"x": 1}, "arguments": {}}},
                                         {"id": 2, "method": "tools/call", "params": {"arguments": {}}},
                                         {"id": 3, "method": "ping"}])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual([reply["id"] for reply in replies], [1, 2, 3])
                for reply in replies[:2]:
                    self.assertEqual(json.loads(reply["result"]["content"][0]["text"])["error"], "invalid_arguments")
                recorded, errors = read_trace(trace, case_id, load(suite, "mock_mcp").SERVER)
                self.assertEqual(errors, [])
                self.assertEqual([call["name"] for call in recorded], [{"x": 1}, None])
                outcome = load(suite, "score").score(case_with_id(cases_of(suite), case_id), recorded, "")
                self.assertIn("call with invalid arguments: None", outcome["errors"])

    def test_an_integral_number_counts_as_an_integer(self):
        self.assertIsNone(schema_error({"type": "integer", "minimum": 1}, 1.0))
        self.assertEqual(schema_error({"type": "integer"}, 1.5), "arguments must be integer")
        self.assertEqual(schema_error({"type": "integer"}, True), "arguments must be integer")

    def test_an_integral_number_reaches_the_fixture_as_an_integer_and_is_recorded_as_sent(self):
        mock = load("compatibility", "mock_mcp")
        fixture = mock.Fixture(case_with_id(cases_of("compatibility"), "run-history-pages"))
        url = f"session://{mock.SPACE}/{mock.OWN_CHAT['id']}"
        self.assertFalse(fixture.call("list_session_events", {"session_url": url, "count": 2.0})["isError"])
        self.assertFalse(fixture.call("read_session_event", {"session_url": url, "sequence": float(mock.CONFIGURATION_EVENT)})["isError"])
        self.assertEqual(fixture.calls[0]["arguments"]["count"], 2.0)

    def test_every_tool_schema_uses_only_what_the_fixture_validates(self):
        for suite in SUITES:
            mock = load(suite, "mock_mcp")
            for tool in mock.TOOLS + getattr(mock, "RUN_HISTORY_TOOLS", []):
                for schema in schemas(tool["inputSchema"]):
                    with self.subTest(suite=suite, tool=tool["name"]):
                        self.assertLessEqual(set(schema), SCHEMA_KEYWORDS)
                        self.assertIn(schema.get("type", "string"), TYPES)


if __name__ == "__main__":
    unittest.main()
