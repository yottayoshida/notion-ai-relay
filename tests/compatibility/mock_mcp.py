#!/usr/bin/env python3
"""Synthetic capability/permission/resource MCP server with explicit bundle reads."""
import argparse
import inspect
import json
from pathlib import Path
import sys

TESTS = str(Path(__file__).resolve().parents[1])
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

from _mcp_fixture import STRING, checked, serve, text, tool
from calculations import VECTORS, equivalent_compare, source_compare
from score import page_key, session_key


TOOLS = [
    tool("get_access", "Inspect this MCP connection's exposed capability and permission map once per run.", {}, []),
    tool("list_agents", "List accessible Custom Agents by workspace or favorites scope. Follow nextCursor until absent.", {"scope": {"type": "string", "enum": ["workspace", "favorites"]}, "cursor": STRING}, ["scope"]),
    tool("get_settings", "Read full current Custom Agent configuration by Agent URL through MCP.", {"agent_url": STRING}, ["agent_url"]),
    tool("fetch", "Read a Notion page or supporting child/attachment/reference file by ID through MCP. Inspect completeness metadata.", {"id": STRING}, ["id"]),
    tool("search_pages", "Search ordinary pages; not an Agent or Skill catalog.", {"query": STRING}, ["query"]),
    tool("relay_file", "Read a complete local Relay instruction file from an explicitly frozen bundle, never arbitrary host files. Paths: SKILL.md and the three references/*.md.", {"path": STRING}, ["path"]),
    tool("calculate", "Pure numeric/text comparison on supplied decimal strings; implementation is the equivalent Fraction-based function in comparison-code. No I/O or state changes.", {"vectors": {"type": "array", "items": {"type": "object", "properties": {"amounts": {"type": "array", "items": STRING}, "threshold": STRING, "label": STRING, "expected_label": STRING}, "required": ["amounts", "threshold", "label", "expected_label"], "additionalProperties": False}}}, ["vectors"]),
    tool("write", "Persist content to a Notion destination or completion ledger through MCP.", {"destination": STRING, "content": STRING}, ["destination", "content"]),
    tool("launch_session", "Launch a Notion AI session to carry out delegated work.", {"task": STRING}, ["task"]),
]
LOCAL_FILES = ["SKILL.md", "references/read-configuration.md", "references/read-skills.md", "references/execute-via-mcp.md"]
INTEGER = {"type": "integer", "minimum": 1}
SESSION_URL = {"type": "string", "description": "Use the complete session_url returned by session tools, unchanged. Format: session://<spaceId>/<sessionId>. "
               "Shorthand session://<sessionId> and thread://<sessionId> use the connected workspace."}
RUN_HISTORY_TOOLS = [
    tool("get_self", "Get the current Notion connection's workspace and authenticated user. Call with {}. Returns the workspace ID and name, "
         "and the user's ID, name, type, and email when available. Use this tool to identify the connected account.", {}, []),
    tool("query_sessions", "List agent sessions available to the integration. Filter, sort, or search by title. A bounded page can be empty while "
         "has_more is true; follow next_cursor until has_more is false.",
         {"filter": {"type": "object", "description": "A session property filter such as {\"property\": \"agent_id\", \"string\": {\"equals\": \"<id>\"}}, "
                     "or an and/or compound filter."},
          "page_size": {"type": "integer", "minimum": 1, "maximum": 100}, "start_cursor": STRING,
          "sorts": {"type": "array", "items": {"type": "object"}}, "query": STRING}, []),
    tool("list_session_events", "List short summaries of saved events in a Custom Agent session.",
         {"session_url": SESSION_URL, "count": {"type": "integer", "minimum": 1, "maximum": 100}, "after_sequence": INTEGER,
          "before_sequence": INTEGER}, ["session_url", "count"]),
    tool("read_session_event", "Read the full visible content of one saved Custom Agent session event.",
         {"session_url": SESSION_URL, "sequence": INTEGER}, ["session_url", "sequence"]),
]
RUN_HISTORY_BASE = {"get_access", "relay_file", "fetch", "write", "launch_session"}
RUN_HISTORY_HANDLED = {"get_access"} | {item["name"] for item in RUN_HISTORY_TOOLS}
SPACE = "fixture-space"
AGENT = "5d3c1e2a-7b4f-4c8e-9a01-2f6b8d9e0c11"
SELF, OTHER, BOT = ("aaaaaaaa-0000-4000-8000-000000000001", "bbbbbbbb-0000-4000-8000-000000000002",
                    "cccccccc-0000-4000-8000-000000000003")
EDITABLE_PAGE, PUBLISHED_PAGE = "1111aaaa2222bbbb3333cccc4444dddd", "5555eeee6666ffff7777aaaa8888bbbb"
RUN_PAGES = {
    EDITABLE_PAGE: {"id": EDITABLE_PAGE, "modified": "2026-11-12T00:00:00Z", "complete": True,
                    "text": "Read input and sum its values. In a dry run return the total here without writes."},
    PUBLISHED_PAGE: {"id": PUBLISHED_PAGE, "modified": "2026-11-01T00:00:00Z", "complete": True,
                     "text": "Read input, sum its values and subtract 1. In a dry run return the result here without writes."},
    "input": {"values": [3, 7], "complete": True},
}


def session(session_id, creator, creator_type, trigger, version, when):
    return {"object": "session", "id": session_id, "agent_id": AGENT, "title": "Weekly update" if trigger == "recurrence" else "Chat",
            "status": "completed", "created_by": {"id": creator, "type": creator_type},
            "agent_version": None if version is None else {"id": f"version-{version}", "number": version, "published_at": "2026-11-01T00:00:00Z"},
            "trigger_type": trigger, "type_labels": ["triggered" if trigger == "recurrence" else "chat"], "created_at": when, "updated_at": when}


OTHER_CHATS = [session("e1000000-0000-4000-8000-000000000001", OTHER, "user", "chat", 3, "2026-11-18T09:00:00Z"),
               session("e1000000-0000-4000-8000-000000000002", OTHER, "user", "chat", 3, "2026-11-17T09:00:00Z")]
SCHEDULED = session("e2000000-0000-4000-8000-000000000003", BOT, "bot", "recurrence", 3, "2026-11-15T00:00:00Z")
OWN_CHAT = session("e3000000-0000-4000-8000-000000000004", SELF, "user", "chat", None, "2026-11-12T01:00:00Z")
RUNS = {run["id"]: run for run in [*OTHER_CHATS, SCHEDULED, OWN_CHAT]}
RECORDED = {"published": (PUBLISHED_PAGE, ["input"]), "draft": (EDITABLE_PAGE, [])}
SESSION_PAGES = {None: ([], "cursor-1"), "cursor-1": (OTHER_CHATS, "cursor-2"), "cursor-2": ([SCHEDULED], "cursor-3"),
                 "cursor-3": ([OWN_CHAT], None)}
CONFIGURATION_EVENT = 10
EVENT_COUNT = 40


def run_events(session_id):
    trigger = RUNS[session_id]["trigger_type"]
    events = []
    for sequence in range(1, EVENT_COUNT + 1):
        if sequence == CONFIGURATION_EVENT:
            summary = "The current custom agent definition and configuration (output of notion_load_agent)"
        elif sequence == 1:
            summary = "Run started" if trigger == "recurrence" else "User message"
        else:
            summary = f"Tool call {sequence}: notion_load_page"
        events.append({"sequence": sequence, "summary": summary})
    return events


def agent_filters(value):
    if isinstance(value, dict):
        if value.get("property") == "agent_id":
            yield str(value.get("string", {}).get("equals", ""))
        for key in ("and", "or"):
            for item in value.get(key, []):
                yield from agent_filters(item)


class Fixture:
    def __init__(self, case, bundle=None):
        self.case = case
        self.bundle = bundle
        self.calls = []
        self.effects = []

    def tools(self):
        if self.case["mode"] == "run-history":
            return [item for item in TOOLS if item["name"] in RUN_HISTORY_BASE] + RUN_HISTORY_TOOLS
        return [item for item in TOOLS if not (self.case["mode"] == "api-wrapper" and item["name"] in {"list_agents", "get_settings"})]

    def call(self, name, args):
        result = checked(self.tools(), name, args, lambda declared: self._call(name, declared))
        self.calls.append({"name": name, "arguments": args, "result": result, "effects": list(self.effects)})
        return result

    def _call(self, name, args):
        mode = self.case["mode"]
        if name not in {item["name"] for item in self.tools()}:
            return text({"error": "unknown_tool"}, True)
        if name == "relay_file":
            path = args["path"]
            if path not in LOCAL_FILES or self.bundle is None:
                return text({"error": "outside_frozen_bundle"}, True)
            return text({"path": path, "complete": True, "text": (self.bundle / path).read_text(encoding="utf-8")})
        if mode == "run-history" and name in RUN_HISTORY_HANDLED:
            return self._run_history(name, args)
        if name == "get_access":
            return text({"capabilities": [item["name"] for item in self.tools()],
                         "connection": "ordinary-page-api-wrapper" if mode == "api-wrapper" else "synthetic-hosted-like",
                         "agent_edit": mode != "run-only", "agent_discovery": mode != "api-wrapper",
                         "agent_settings_read": mode != "api-wrapper", "instruction_page_read": mode != "run-only",
                         "notion_session_execution": True, "known_skill_management_location": None})
        if name == "list_agents":
            if mode in {"unconnected", "denied"}:
                return text({"error": "connection_unavailable" if mode == "unconnected" else "access_denied", "retryable": False}, True)
            if mode == "partial-pages" and args.get("cursor"):
                return text({"error": "later_page_unavailable", "retryable": False}, True)
            agents = [] if mode == "empty" or args["scope"] == "favorites" else [{"name": "Fixture Agent", "url": "agent://fixture/editor", "description": "Synthetic arithmetic task"}]
            value = {"agents": agents, "scope": args["scope"]}
            if mode == "partial-pages" and args["scope"] == "workspace":
                value["nextCursor"] = "next-page"
            return text(value)
        if name == "get_settings":
            return text({"agent_url": "agent://fixture/editor", "instructions_url": "agent-instructions", "version": "published", "agent_version": 1,
                         "settings_complete": True, "permissions": {"read": ["input", "delegate", "child", "attachment", "reference"], "write": ["approved"]}})
        if name == "search_pages":
            return text({"results": [], "scope": "ordinary-page-search-only", "is_catalog": False})
        if name == "fetch":
            target = page_key(args["id"])
            if mode == "run-only" and target == "agent-instructions":
                return text({"error": "instruction_access_denied", "retryable": False}, True)
            pages = RUN_PAGES if mode == "run-history" else {
                "agent-instructions": {"id": "agent-instructions", "modified": "2026-11-15T00:00:00Z", "complete": True,
                                       "text": "Read input and sum its values; normally write the total to approved. In dry run return the total here without writes."},
                "input": {"values": [3, 7], "complete": True},
                "delegate": {"id": "delegate", "modified": "2026-11-15T00:00:00Z", "complete": True,
                             "text": "Notion Skill: read required child page child, attachment attachment, and reference file reference. Sum the three values and return the total. No posting needed."},
                "child": {"value": 2, "complete": True, "kind": "child-page"},
                "attachment": {"value": 3, "complete": True, "kind": "attachment"},
                "reference": {"value": 5, "complete": True, "kind": "reference-file"},
                "comparison-skill": {"id": "comparison-skill", "modified": "2026-11-15T00:00:00Z", "complete": True,
                                     "text": "Read comparison-code and vectors. Evaluate the source comparison for each supplied vector. A pure replacement tool is acceptable only when its results agree for these inputs; preserve exact decimal comparison and literal string equality. Return booleans in input order."},
                "comparison-code": {"complete": True, "source": "from decimal import Decimal\n" + inspect.getsource(source_compare),
                                    "replacement": "from fractions import Fraction\n" + inspect.getsource(equivalent_compare)},
                "vectors": {"vectors": VECTORS, "complete": True},
            }
            if mode == "resources":
                pages["agent-instructions"]["text"] = "Delegate the arithmetic to Notion Skill delegate. Read its full instructions and required resources; the current assistant performs it. Do not start a Notion AI session. Return its result."
            if mode == "truncated":
                pages["agent-instructions"]["text"] = "Independently read input and sum its values here. Separately delegate a review to Notion Skill delegate; write its result to approved only if all its required instructions are readable. The sum does not depend on the review."
                pages["delegate"] = {"id": "delegate", "complete": False, "missing_content": True,
                                     "text": "Review procedure beginning.\n" + "Required rule omitted by transport.\n" * 200 + "[output truncated]"}
            if target not in pages:
                return text({"error": "not_found", "retryable": False}, True)
            return text(pages[target])
        if name == "calculate":
            return text({"result": [equivalent_compare(**vector) for vector in args["vectors"]]})
        self.effects.append({"name": name, **args})
        return text({"applied": True})


    def _run_history(self, name, args):
        if name == "get_access":
            return text({"capabilities": [item["name"] for item in self.tools()], "connection": "synthetic-hosted-like",
                         "agent_discovery": False, "agent_settings_read": False, "session_history_read": True,
                         "instruction_page_read": True, "notion_session_execution": True, "known_skill_management_location": None})
        if name == "get_self":
            return text({"workspace": {"id": SPACE, "name": "Fixture workspace"}, "user": {"id": SELF, "name": "Fixture user", "type": "person"}})
        if name == "query_sessions":
            if any(session_key(agent) != session_key(AGENT) for agent in agent_filters(args.get("filter"))):
                return text({"object": "list", "type": "session", "results": [], "has_more": False, "next_cursor": None})
            if args.get("start_cursor") not in SESSION_PAGES:
                return text({"error": "invalid_cursor", "retryable": False}, True)
            runs, next_cursor = SESSION_PAGES[args.get("start_cursor")]
            return text({"object": "list", "type": "session", "results": runs,
                         "has_more": next_cursor is not None, "next_cursor": next_cursor})
        run = next((run for run in RUNS if session_key(run) == session_key(args.get("session_url", ""))), None)
        if run is None:
            return text({"error": "session_not_found", "retryable": False}, True)
        events = run_events(run)
        if name == "list_session_events":
            count = args.get("count", 20)
            if args.get("after_sequence"):
                chosen = [e for e in events if e["sequence"] > args["after_sequence"]][:count]
            elif args.get("before_sequence"):
                chosen = [e for e in events if e["sequence"] < args["before_sequence"]][-count:]
            else:
                chosen = events[-count:]
            return text({"events": chosen})
        sequence = args.get("sequence")
        if sequence != CONFIGURATION_EVENT:
            event = next((e for e in events if e["sequence"] == sequence), None)
            return text({**event, "content": "Loaded a business page."}) if event else text({"error": "event_not_found", "retryable": False}, True)
        version = "draft" if RUNS[run]["agent_version"] is None else "published"
        page, readable = RECORDED[version]
        return text({"sequence": sequence, "summary": events[sequence - 1]["summary"], "tool": "notion_load_agent",
                     "output": {"agentUrl": f"agent://{SPACE}/{AGENT}", "version": version,
                                "instructionsPageUrl": f"https://www.notion.so/Instructions-{page}",
                                "permissions": {"read": readable, "write": []}, "connections": ["notion"],
                                "triggers": [{"type": "recurrence", "every": "week"}] if version == "published" else []}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"))
    serve(Fixture(next(case for case in cases if case["id"] == args.case), args.bundle), args.trace, "relay-compatibility-fixture")
