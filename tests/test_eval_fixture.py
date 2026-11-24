import json
from pathlib import Path
import tempfile
import unittest

from _support import load, read_trace, stdio

mock = load("eval-fixture", "mock_mcp")
SUITE = "eval-fixture"
ALL_CASES = [(suite, case) for suite in mock.SUITES for case in mock.cases(suite)]
by_id = mock.load_case


def payload(result):
    return json.loads(result["content"][0]["text"])


def every_call(case):
    ids = ["fixture://procedure", "fixture://items", "unknown-id",
           *(record["id"] for record in case.get("items", {}).get("records", []))]
    calls = [("access", {})] + [("fetch", {"id": target}) for target in ids]
    calls += [("search_agents", {"scope": scope}) for scope in ("favorites", "workspace")]
    calls += [("search_agents", {"scope": "workspace", "query": "weekly"})]
    calls += [("update", {"id": target, "status": "Done"}) for target in ids]
    calls += [("send", {"destination": "#ops-weekly", "content": "x"}), ("save_state", {"content": "x"}),
              ("enable_access", {"capability": "agents"})]
    return calls


class EvalFixtureTests(unittest.TestCase):
    def test_each_case_offers_only_the_tools_it_declares(self):
        for suite, case in ALL_CASES:
            with self.subTest(suite=suite, case=case["id"]):
                self.assertEqual({tool["name"] for tool in mock.Fixture(case).tools()}, set(case.get("tools", mock.DEFAULT_TOOLS)))

    def test_a_tool_the_case_does_not_offer_is_refused_and_recorded_without_an_effect(self):
        fixture = mock.Fixture(by_id("next-step", "notion-not-connected"))
        result = fixture.call("fetch", {"id": "fixture://procedure"})
        self.assertTrue(result["isError"])
        self.assertEqual(payload(result)["error"], "unknown_tool")
        self.assertEqual(([call["name"] for call in fixture.calls], fixture.effects), (["fetch"], []))

    def test_an_update_changes_what_later_reads_return(self):
        fixture = mock.Fixture(by_id("dry-run", "preview-partial"))
        self.assertFalse(fixture.call("update", {"id": "page-A", "status": "Done"})["isError"])
        self.assertEqual(payload(fixture.call("fetch", {"id": "page-A"}))["status"], "Done")
        self.assertEqual(payload(fixture.call("fetch", {"id": "fixture://page-A"}))["status"], "Done")
        self.assertEqual(payload(fixture.call("fetch", {"id": "fixture://items"}))["records"][0]["status"], "Done")
        self.assertEqual(fixture.effects, [{"name": "update", "id": "page-A", "status": "Done"}])

    def test_updates_are_kept_per_fixture_not_written_back_to_the_case(self):
        case = by_id("dry-run", "preview-partial")
        mock.Fixture(case).call("update", {"id": "page-A", "status": "Done"})
        self.assertEqual(payload(mock.Fixture(case).call("fetch", {"id": "page-A"}))["status"], "Ready")

    def test_sends_state_saves_and_capability_changes_are_recorded_as_effects(self):
        fixture = mock.Fixture(by_id("next-step", "agent-tools-refused"))
        fixture.call("enable_access", {"capability": "agents"})
        self.assertEqual(fixture.effects, [{"name": "enable_access", "capability": "agents"}])
        fixture = mock.Fixture(by_id("dry-run", "preview-partial"))
        fixture.call("send", {"destination": "C-FIXTURE", "content": "summary"})
        fixture.call("save_state", {"content": "resume"})
        self.assertEqual([effect["name"] for effect in fixture.effects], ["send", "save_state"])

    def test_an_update_of_an_unknown_record_is_an_error_not_an_effect(self):
        fixture = mock.Fixture(by_id("dry-run", "preview-partial"))
        self.assertEqual(payload(fixture.call("update", {"id": "page-Z", "status": "Done"}))["error"], "not_found")
        self.assertEqual(fixture.effects, [])

    def test_a_denied_call_returns_the_cases_refusal_unchanged(self):
        case = by_id("next-step", "agent-tools-refused")
        for scope in ("favorites", "workspace"):
            result = mock.Fixture(case).call("search_agents", {"scope": scope})
            self.assertTrue(result["isError"])
            self.assertEqual(payload(result), case["denied"]["search_agents"])
        case = by_id("next-step", "source-denied")
        fixture = mock.Fixture(case)
        self.assertEqual(payload(fixture.call("fetch", {"id": "fixture://policy"})), case["denied"]["fetch:fixture://policy"])
        self.assertFalse(fixture.call("fetch", {"id": "fixture://procedure"})["isError"])

    def test_a_denied_update_changes_nothing(self):
        case = by_id("next-step", "write-denied")
        fixture = mock.Fixture(case)
        record = case["items"]["records"][0]["id"]
        self.assertTrue(fixture.call("update", {"id": record, "status": "Done"})["isError"])
        self.assertEqual(payload(fixture.call("fetch", {"id": record}))["status"], "Ready")
        self.assertEqual(fixture.effects, [])

    def test_a_search_without_a_query_lists_the_scope_and_a_query_matches_name_or_description(self):
        case = by_id("next-step", "agent-not-found")
        fixture = mock.Fixture(case)
        listed = payload(fixture.call("search_agents", {"scope": "workspace"}))["results"]
        self.assertEqual(listed, case["agents"]["workspace"])
        self.assertEqual(payload(fixture.call("search_agents", {"scope": "workspace", "query": "weekly digest"}))["results"], [])
        found = payload(mock.Fixture(by_id("next-step", "instructions-unreadable")).call(
            "search_agents", {"scope": "workspace", "query": "WEEKLY"}))["results"]
        self.assertEqual([agent["name"] for agent in found], ["Weekly digest"])

    def test_no_tool_result_depends_on_the_expected_outcome(self):
        for suite, case in ALL_CASES:
            hidden = {key: value for key, value in case.items() if not key.startswith("expected")}
            with self.subTest(suite=suite, case=case["id"]):
                with_expected, without_expected = mock.Fixture(case), mock.Fixture(hidden)
                for name, arguments in every_call(case):
                    self.assertEqual(with_expected.call(name, arguments), without_expected.call(name, arguments))

    def test_the_server_records_every_call_as_ascii_including_calls_it_cannot_process(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            calls = [("fetch", {}), ("fetch", {"id": "fixture://items", "page": 2}), ("update", {"id": "page-A", "status": 1}),
                     ("send", {"destination": "#ops", "content": "報告 → 10"})]
            requests = [{"id": index, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
                        for index, (name, arguments) in enumerate(calls, 1)]
            result, replies = stdio(SUITE, ["--suite", "dry-run", "--case", "preview-partial", "--trace", trace],
                                    [{"id": 0, "method": "tools/list"}, *requests])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([tool["name"] for tool in replies[0]["result"]["tools"]], mock.DEFAULT_TOOLS)
            self.assertEqual([payload(reply["result"]).get("error") for reply in replies[1:]], ["invalid_arguments"] * 3 + [None])
            self.assertTrue(trace.read_bytes().isascii())
            recorded, errors = read_trace(trace, "preview-partial", mock.SERVER)
            self.assertEqual((errors, [(call["name"], call["arguments"]) for call in recorded]), ([], calls))

if __name__ == "__main__":
    unittest.main()
