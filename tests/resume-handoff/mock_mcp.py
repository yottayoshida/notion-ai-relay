#!/usr/bin/env python3
"""Synthetic MCP stdio fixture for resume-handoff cases. No network, shell, or business-data access."""
import argparse
from pathlib import Path
import sys

TESTS = str(Path(__file__).resolve().parents[1])
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

from _mcp_fixture import checked, serve, text, tool

SERVER = "relay-resume-fixture"
TARGET = "agent://fixture-workspace/weekly-relay"
CONFIGURATION_URL = "https://www.notion.so/11111111111111111111111111111111"
OPERATIONS = ["get_configuration", "read_run_state", "read_item", "read_result",
              "create_result", "advance_checkpoint", "save_resume_record", "rollback"]
ITEMS = ["A", "B", "C"]
ITEM_OPERATIONS = {"read_item", "read_result", "create_result", "advance_checkpoint"}
INITIAL_CHECKPOINT = ["A"]
TOOLS = [tool("mock_mcp", "Synthetic resume-handoff operations. Give the operation; read_item, read_result, "
              "create_result and advance_checkpoint also take an item, A, B or C.",
              {"operation": {"type": "string", "enum": OPERATIONS}, "item": {"type": "string", "enum": ITEMS}},
              ["operation"])]
INSTRUCTIONS = (
    "Process A, B and C in order for the requested batch and period. "
    "Read each input before creating a missing result in fixture-results. "
    "Look up existing results first and do not duplicate them. "
    "Read each result back to verify it; advance the existing batch checkpoint "
    "only for verified work. Hold work whose required input is unreadable; "
    "preserve independent verified progress. On normal success return only "
    "JSON with the one key completed, listing A, B, C. No scheduled execution, "
    "strict concurrent-run prevention, or local persistent resume record is required.")


class Fixture:
    def __init__(self, case):
        self.case = case
        self.results = {"A": "result-A", "B": "result-B"} if case["id"] == "normal-resume-output-only" else {"A": "result-A"}
        self.checkpoint = list(INITIAL_CHECKPOINT)
        self.verified = ["A"]
        self.calls = []

    def tools(self):
        return TOOLS

    def call(self, name, arguments):
        record = {"name": name, "arguments": arguments, "verified_before": list(self.verified)}
        self.calls.append(record)
        record["result"] = checked(TOOLS, name, arguments, lambda args: self.answer(name, args))
        record["checkpoint_after"] = list(self.checkpoint)
        return record["result"]

    def answer(self, name, args):
        value = self.operate(args["operation"], args.get("item")) if name == "mock_mcp" else {"error": "unknown tool"}
        return text(value, "error" in value)

    def operate(self, operation, item):
        if operation in ITEM_OPERATIONS and item is None:
            return {"error": "invalid_arguments", "message": "item is required"}
        if operation == "get_configuration":
            return {"target": TARGET, "instructions_url": CONFIGURATION_URL,
                    "modified_at": "2026-06-01T00:00:00Z", "instructions": INSTRUCTIONS}
        if operation == "read_run_state":
            if "runs" not in self.case:
                return {"checkpoint": list(self.checkpoint), "input_id": "batch-june"}
            return {"runs": self.case["runs"]}
        if operation == "read_item":
            if self.case["id"] == "partial-dry-run" and item == "C":
                return {"error": "access_denied", "target": "input-C"}
            return {"id": f"input-{item}", "content": f"synthetic value {item}"}
        if operation == "read_result":
            if item not in self.results:
                return {"found": False, "item": item}
            if item not in self.verified:
                self.verified.append(item)
            return {"found": True, "item": item, "url": self.results[item],
                    "content": f"synthetic value {item}", "verified": True}
        if operation == "create_result":
            self.results[item] = f"result-{item}"
            return {"url": self.results[item], "item": item}
        if operation == "advance_checkpoint":
            if item not in self.checkpoint:
                self.checkpoint.append(item)
            return {"checkpoint": list(self.checkpoint)}
        return {"recorded": operation}


if __name__ == "__main__":
    from _support import case_with_id, cases_of
    cases = cases_of(Path(__file__).parent.name)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=[case["id"] for case in cases])
    parser.add_argument("--trace", type=Path, required=True)
    args = parser.parse_args()
    serve(Fixture(case_with_id(cases, args.case)), args.trace, SERVER)
