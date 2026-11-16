#!/usr/bin/env python3
"""Synthetic capability/permission/resource MCP server with explicit bundle reads."""
import argparse
import inspect
import json
from pathlib import Path
import sys

from calculations import VECTORS, equivalent_compare, source_compare


STRING = {"type": "string"}


def tool(name, description, properties, required):
    return {"name": name, "description": description, "inputSchema": {
        "type": "object", "properties": properties, "required": required, "additionalProperties": False}}


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


def text(value, error=False):
    return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}], "isError": error}


class Fixture:
    def __init__(self, case, bundle=None):
        self.case = case
        self.bundle = bundle
        self.calls = []
        self.effects = []

    def tools(self):
        return [item for item in TOOLS if not (self.case["mode"] == "api-wrapper" and item["name"] in {"list_agents", "get_settings"})]

    def call(self, name, args):
        result = self._call(name, args)
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
            return text({"path": path, "complete": True, "text": (self.bundle / path).read_text()})
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
            target = args["id"]
            if mode == "run-only" and target == "agent-instructions":
                return text({"error": "instruction_access_denied", "retryable": False}, True)
            pages = {
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


def serve(case, trace, bundle):
    fixture = Fixture(case, bundle)
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        method = request["method"]
        if method == "initialize":
            result = {"protocolVersion": request["params"]["protocolVersion"], "capabilities": {"tools": {}},
                      "serverInfo": {"name": "relay-compatibility-fixture", "version": "1"}}
        elif method == "tools/list":
            result = {"tools": fixture.tools()}
        elif method == "tools/call":
            params = request["params"]
            result = fixture.call(params["name"], params.get("arguments", {}))
            with trace.open("a") as out:
                out.write(json.dumps(fixture.calls[-1], ensure_ascii=False) + "\n")
        elif method == "ping":
            result = {}
        else:
            print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "error": {"code": -32601, "message": "Unknown method"}}), flush=True)
            continue
        print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads(Path(__file__).with_name("cases.json").read_text())
    serve(next(case for case in cases if case["id"] == args.case), args.trace, args.bundle)
