import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from _mcp_fixture import split_malformed, split_rejected, start_record, text
from _support import TESTS, load, read_trace, run, stdio, write_trace

CALL = {"name": "fetch", "arguments": {"id": "x"}, "result": text({"value": 1})}
FIXTURES = {
    "security": ["--case", "authorized-normal"],
    "compatibility": ["--case", "comparison-code", "--bundle", TESTS.parent],
    "write-lifecycle": ["--case", "normal"],
    "resume-handoff": ["--case", "partial-dry-run"],
}
BROKEN_REQUESTS = [
    (b'{"jsonrpc": "2.0", "id": 1}', {"id": 1, "error": {"code": -32600, "message": "Invalid request"}}),
    (b'{"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {}}',
     {"id": 2, "error": {"code": -32602, "message": "Invalid params: protocolVersion is required"}}),
    (b"5", {"id": None, "error": {"code": -32600, "message": "Invalid request"}}),
    (b"", None),
    (b"not json", {"id": None, "error": {"code": -32700, "message": "Parse error"}}),
    (b'{"jsonrpc": "2.0", "id": 3, "method": "ping", "note": "\xff"}', {"id": None, "error": {"code": -32700, "message": "Parse error"}}),
    (b'{"jsonrpc": "2.0", "id": 4, "method": "initialize"}',
     {"id": 4, "error": {"code": -32602, "message": "Invalid params: protocolVersion is required"}}),
    (b'{"jsonrpc": "2.0", "id": 5, "method": "ping", "params": [1]}', {"id": 5, "error": {"code": -32602, "message": "Invalid params"}}),
    (b'{"jsonrpc": "2.0", "method": "notifications/initialized"}', None),
    (b'{"jsonrpc": "2.0", "id": 6, "method": "tools/call"}',
     {"id": 6, "result": text({"error": "invalid_arguments", "message": "name must be string"}, True)}),
]
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
        for suite, (_, case_id, *arguments) in FIXTURES.items():
            server = load(suite, "mock_mcp").SERVER
            with self.subTest(suite=suite), tempfile.TemporaryDirectory() as directory:
                trace = Path(directory) / "trace.jsonl"
                for _ in range(2):
                    result, replies = stdio(suite, ["--case", case_id, "--trace", trace, *arguments], [{"id": 1, "method": "ping"}])
                    self.assertEqual((result.returncode, [reply["id"] for reply in replies]), (0, [1]), result.stderr)
                lines = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
                self.assertEqual(lines, [start_record(case_id, server)] * 2)


class ScorerCliInputTests(unittest.TestCase):
    def test_a_missing_or_non_utf8_input_is_named_without_a_traceback(self):
        for suite, (_, case_id, *_) in FIXTURES.items():
            with self.subTest(suite=suite), tempfile.TemporaryDirectory() as directory:
                garbled = Path(directory) / "garbled.txt"
                garbled.write_bytes(b"\xff\xfe")
                valid = Path(directory) / "trace.jsonl"
                write_trace(valid, case_id, load(suite, "mock_mcp").SERVER, [])
                attempts = [([Path(directory) / "missing.jsonl", garbled], Path(directory) / "missing.jsonl"),
                            ([garbled, garbled], garbled), ([valid, garbled], garbled)]
                if suite == "write-lifecycle":
                    attempts.append(([valid, valid, "--first-report", garbled], garbled))
                for files, unreadable in attempts:
                    result = run(suite, "score.py", [case_id, *files])
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertIn(f"cannot read {unreadable}", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)


class ReceiveLoopTests(unittest.TestCase):
    def test_the_fixture_answers_the_handshake_and_a_broken_request_without_stopping(self):
        for suite, arguments in FIXTURES.items():
            with self.subTest(suite=suite), tempfile.TemporaryDirectory() as directory:
                handshake = [
                    (b'{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2099-01-01"}}',
                     {"id": 0, "result": {"protocolVersion": "2099-01-01", "capabilities": {"tools": {}},
                                          "serverInfo": {"name": load(suite, "mock_mcp").SERVER, "version": "1"}}}),
                    (b'{"jsonrpc": "2.0", "id": 8, "method": "resources/list"}', {"id": 8, "error": {"code": -32601, "message": "Unknown method"}}),
                ]
                exchange = handshake[:1] + BROKEN_REQUESTS + handshake[1:] + [(b'{"jsonrpc": "2.0", "id": 9, "method": "ping"}', {"id": 9, "result": {}})]
                result = subprocess.run([sys.executable, str(TESTS / suite / "mock_mcp.py"), *map(str, arguments),
                                         "--trace", str(Path(directory) / "trace.jsonl")],
                                        input=b"".join(line + b"\n" for line, _ in exchange), capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                replies = [json.loads(line) for line in result.stdout.decode("utf-8").splitlines()]
                self.assertEqual(replies, [{"jsonrpc": "2.0", **reply} for _, reply in exchange if reply is not None])


if __name__ == "__main__":
    unittest.main()
