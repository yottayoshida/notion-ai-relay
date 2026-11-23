import json
from pathlib import Path
import tempfile
import unittest

from _mcp_fixture import split_malformed, split_rejected, start_record, text
from _support import TESTS, load, read_trace, stdio

CALL = {"name": "fetch", "arguments": {"id": "x"}, "result": text({"value": 1})}
START = json.dumps(start_record("case-a", "server-a"))


def read(lines):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "trace.jsonl"
        path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
        return read_trace(path, "case-a", "server-a")


class TraceFileTests(unittest.TestCase):
    def test_a_trace_of_one_run_of_the_expected_case_gives_back_its_calls(self):
        self.assertEqual(read([START, json.dumps(CALL)]), ([CALL], []))

    def test_a_trace_that_is_not_one_run_of_the_expected_case_and_server_is_refused(self):
        other_case = json.dumps(start_record("case-b", "server-a"))
        other_server = json.dumps(start_record("case-a", "server-b"))
        for label, lines, error in [
            ("empty", [], "trace has no start line"),
            ("calls only", [json.dumps(CALL)], "trace has no start line"),
            ("two runs", [START, json.dumps(CALL), START], "trace holds more than one run"),
            ("start after a call", [json.dumps(CALL), START], "trace does not begin with its start line"),
            ("another case", [other_case], f"trace starts another run: {other_case}"),
            ("another server", [other_server], f"trace starts another run: {other_server}"),
            ("blank line", [START, ""], "trace line 2 is not a JSON object"),
            ("line that is not JSON", [START, "{"], "trace line 2 is not a JSON object"),
            ("line that is not an object", [START, "[]"], "trace line 2 is not a JSON object"),
        ]:
            with self.subTest(label):
                self.assertEqual(read(lines)[1], [error])


class CallRecordTests(unittest.TestCase):
    def test_a_complete_record_is_kept_and_an_error_result_needs_no_json(self):
        failure = {**CALL, "result": text("Host permission denied", True)}
        self.assertEqual(split_malformed([CALL, failure]), ([CALL, failure], []))

    def test_a_record_without_a_usable_name_arguments_or_result_is_set_aside_by_name(self):
        for label, record, name in [
            ("not an object", ["fetch"], None),
            ("name not a string", {**CALL, "name": 7}, 7),
            ("arguments not an object", {**CALL, "arguments": ["x"]}, "fetch"),
            ("no result", {"name": "fetch", "arguments": {}}, "fetch"),
            ("result not an object", {**CALL, "result": "ok"}, "fetch"),
            ("no content", {**CALL, "result": {"isError": False}}, "fetch"),
            ("empty content", {**CALL, "result": {"content": [], "isError": False}}, "fetch"),
            ("content without text", {**CALL, "result": {"content": [{"type": "text"}], "isError": False}}, "fetch"),
            ("success text that is not JSON", {**CALL, "result": text("not JSON")}, "fetch"),
            ("success JSON that is not an object", {**CALL, "result": text("[]")}, "fetch"),
        ]:
            with self.subTest(label):
                self.assertEqual(split_malformed([CALL, record]), ([CALL], [name]))

    def test_a_result_the_scorer_does_not_read_may_be_plain_text(self):
        download = {**CALL, "name": "direct_fetch", "result": text("plain archive text")}
        self.assertEqual(split_malformed([download], unparsed={"direct_fetch"}), ([download], []))
        self.assertEqual(split_malformed([download]), ([], ["direct_fetch"]))

    def test_a_record_that_is_not_an_object_is_not_taken_for_a_rejected_call(self):
        self.assertEqual(split_rejected([["fetch"], CALL]), ([["fetch"], CALL], []))


class FixtureStartTests(unittest.TestCase):
    def test_each_fixture_start_appends_one_start_line_for_its_case_and_server(self):
        for suite, case_id, arguments in [("security", "data-injection", []),
                                          ("compatibility", "editor", ["--bundle", TESTS.parent]),
                                          ("write-lifecycle", "normal", [])]:
            server = load(suite, "mock_mcp").SERVER
            with self.subTest(suite=suite), tempfile.TemporaryDirectory() as directory:
                trace = Path(directory) / "trace.jsonl"
                for _ in range(2):
                    result, replies = stdio(suite, ["--case", case_id, "--trace", trace, *arguments], [{"id": 1, "method": "ping"}])
                    self.assertEqual((result.returncode, [reply["id"] for reply in replies]), (0, [1]), result.stderr)
                lines = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
                self.assertEqual(lines, [start_record(case_id, server)] * 2)


if __name__ == "__main__":
    unittest.main()
