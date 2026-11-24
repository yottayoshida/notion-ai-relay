#!/usr/bin/env python3
"""Synthetic MCP stdio fixture for the evals/dry-run and evals/next-step cases. No network, shell, or business-data access."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

TESTS = str(Path(__file__).resolve().parents[1])
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

from _mcp_fixture import STRING, checked, serve, text, tool

SERVER = "relay-eval-fixture"
EVALS = Path(__file__).resolve().parents[2] / "evals"
SUITES = ("dry-run", "next-step")

TOOLS = [
    tool("access", "Report which read, update, and send operations this connection can perform.", {}, []),
    tool("fetch", "Read a page, a list of records, or one record through MCP by its exact ID or URL.", {"id": STRING}, ["id"]),
    tool("update", "Set the status property of one record through MCP.", {"id": STRING, "status": STRING}, ["id", "status"]),
    tool("send", "Post a message to a Slack channel or another destination through MCP.",
         {"destination": STRING, "content": STRING}, ["destination", "content"]),
    tool("save_state", "Persist this run's checkpoint or resume record.", {"content": STRING}, ["content"]),
    tool("search_agents", "Search Custom Agents by name or description, or list the current user's favorite agents or the "
         "workspace's agents without a query. Queries return one page.\n\nRequires Notion AI and Custom Agents access. "
         "Call this tool directly. If access is denied, follow the recovery guidance in the result.",
         {"scope": {"type": "string", "enum": ["favorites", "workspace"]}, "query": STRING}, ["scope"]),
    tool("enable_access", "Turn on a capability for this connection.", {"capability": STRING}, []),
]
DEFAULT_TOOLS = ["access", "fetch", "update", "send", "save_state"]


class Fixture:
    def __init__(self, case):
        self.case = case
        # A copy: updates must not leak into the case, or a second fixture for the same case would start changed.
        self.items = deepcopy(case.get("items", {}))
        self.records = self.items.get("records", [])
        declared = case.get("tools", DEFAULT_TOOLS)
        self.offered = [item for item in TOOLS if item["name"] in declared]
        self.calls = []
        self.effects = []

    def tools(self):
        return self.offered

    def call(self, name, arguments):
        event = {"name": name, "arguments": arguments}
        self.calls.append(event)
        event["result"] = checked(self.tools(), name, arguments, lambda declared: self._call(name, declared))
        return event["result"]

    def record(self, target):
        return next((record for record in self.records if target in (record["id"], record.get("url"))), None)

    def denial(self, name, arguments):
        denied = self.case.get("denied", {})
        return denied.get(f"{name}:{arguments.get('id')}", denied.get(name))

    def page(self, target):
        if target == "fixture://procedure" and "procedure" in self.case:
            return {"id": target, "text": self.case["procedure"]}
        if target == "fixture://items" and self.items:
            return self.items
        return self.record(target)

    def agents(self, scope, query):
        found = self.case.get("agents", {}).get(scope, [])
        if query:
            needle = query.lower()
            found = [agent for agent in found if needle in agent["name"].lower() or needle in agent.get("description", "").lower()]
        return found

    def _call(self, name, arguments):
        if name not in {item["name"] for item in self.offered}:
            return text({"error": "unknown_tool", "message": f"No tool named {name}"}, True)
        if (denial := self.denial(name, arguments)) is not None:
            return text(denial, True)
        if name == "access":
            return text(self.case.get("inventory", {}))
        if name == "fetch":
            found = self.page(arguments["id"])
            return text(found) if found is not None else text({"error": "not_found", "message": "Unknown fixture ID"}, True)
        if name == "search_agents":
            return text({"results": self.agents(arguments["scope"], arguments.get("query"))})
        if name == "update":
            record = self.record(arguments["id"])
            if record is None:
                return text({"error": "not_found", "message": "Unknown record ID"}, True)
            record["status"] = arguments["status"]
        self.effects.append({"name": name, **arguments})
        return text({"ok": True, **arguments})


def cases(suite):
    return json.loads((EVALS / suite / "cases.json").read_text(encoding="utf-8"))["cases"]


def load_case(suite, case_id):
    return next(case for case in cases(suite) if case["id"] == case_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", required=True, choices=SUITES)
    parser.add_argument("--case", required=True)
    parser.add_argument("--trace", type=Path, required=True)
    args = parser.parse_args()
    serve(Fixture(load_case(args.suite, args.case)), args.trace, SERVER)
