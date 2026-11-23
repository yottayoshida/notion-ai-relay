#!/usr/bin/env python3
"""In-memory write lifecycle MCP fixture; only explicit trace paths are written."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

TESTS = str(Path(__file__).resolve().parents[1])
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

from _mcp_fixture import STRING, append, checked, serve, text, tool

OBJECT = {"type": "object", "additionalProperties": STRING}
RELATIONS = {"type": "array", "items": STRING}


TOOLS = [
    tool("fetch", "Read a Notion page, input, checkpoint, or persisted object through MCP. IDs skill and input are procedure/input pages.", {"id": STRING}, ["id"]),
    tool("lookup", "Find persisted objects by logical key through MCP; returns full content, properties, relations and version.", {"key": STRING}, ["key"]),
    tool("create", "Create a Notion object through MCP. No server idempotency: each successful call creates another object, even for the same key.", {"key": STRING, "content": STRING, "properties": OBJECT, "relations": RELATIONS}, ["key", "content", "properties", "relations"]),
    tool("update", "Update an existing Notion object through MCP. Content and relations replace existing values; properties are merged. Optional expected_version is a server-enforced conditional write.", {"id": STRING, "content": STRING, "properties": OBJECT, "relations": RELATIONS, "expected_version": {"type": "integer"}}, ["id", "content", "properties", "relations"]),
    tool("checkpoint", "Persist a verified logical key as complete in the run ledger through MCP. This tool does not verify business effects.", {"key": STRING}, ["key"]),
    tool("delete", "Delete an object through MCP, including previously created effects.", {"id": STRING}, ["id"]),
]


class Fixture:
    def __init__(self, case):
        self.case = case
        self.objects = {"B": {"id": "B", "key": "B", "content": "Existing B", "properties": {"owner": "keep", "status": "todo"}, "relations": ["R0"], "version": 1}}
        self.checkpoints = []
        self.calls = []
        self.creations = 0
        self.phase = 1
        self.flags = set()
        self.stopped = False

    def snapshot(self):
        return deepcopy({"objects": self.objects, "checkpoints": self.checkpoints, "creations": self.creations, "phase": self.phase, "stopped": self.stopped})

    def procedure(self):
        return {"id": "skill", "modified": "2026-11-15T00:00:00Z", "text": (
            "Execute supplied instructions only; no Agent settings are needed. Read input and checkpoint. "
            "Process requested logical keys sequentially in listed order. A and B are independent: a held or unverified A does not block B. "
            "Skip a completed key on resume, preserving its verified result. "
            "For A, lookup key A before creating one object with content 'Created A', properties status=done, relations [R]. "
            "For B, read existing object B; append a newline and 'Processed B' once, merge status=done, and preserve all other content/properties/relations while adding R. "
            "If another user changed it, reassess from current content; do not overwrite their additions. "
            "After every create/update, read the persisted object and verify content, properties and relations before checkpointing the key. "
            "After a create timeout, lookup its logical key to reconcile before considering any resend; zero or unknown results are not proof of no effect. "
            "For a retryable read/rate-limit error, permit at most one retry for that read. Never retry permanent or permission errors in this phase. "
            "When the user stops, perform no subsequent service calls, including verification, checkpoint, or rollback. "
            "Report only JSON with arrays confirmed, unknown, not_executed, held (logical keys, mutually exclusive). "
            "confirmed requires verified business effect and checkpoint; unknown means an attempted write is not verified; "
            "held means a key is blocked before any successful/unknown effect; not_executed means unattempted remaining work after stop. "
            "Disclose reasons in a separate reasons object. Do not claim unknown work completed."
        )}

    def tools(self):
        return TOOLS

    def call(self, name, arguments):
        before = self.snapshot()
        result = checked(self.tools(), name, arguments, lambda declared: self._call(name, declared))
        self.calls.append({"name": name, "arguments": deepcopy(arguments), "phase": self.phase,
                           "after_stop": self.stopped, "before": before, "after": self.snapshot(), "result": result})
        return result

    def _call(self, name, args):
        fault = self.case["fault"]
        if name == "fetch":
            target = args["id"]
            if target == "skill":
                return text(self.procedure())
            if target == "input":
                if fault == "read_rate_limit" and "rate_limit" not in self.flags:
                    self.flags.add("rate_limit")
                    return text({"error": "rate_limited", "retryable": True, "retry_after_seconds": 0}, True)
                return text({"keys": self.case["jobs"], "read_after_write_supported": fault != "no_readback"})
            if target == "checkpoint":
                return text({"complete": self.checkpoints})
            obj = self.objects.get(target)
            if fault == "no_readback":
                return text({"error": "read_after_write_unsupported", "retryable": False}, True)
            if obj and obj["key"] == "A" and fault == "verify_failure":
                return text({"error": "verification_unavailable", "retryable": False}, True)
            return text(obj) if obj else text({"error": "not_found", "retryable": False}, True)
        if name == "lookup":
            if fault == "no_readback":
                return text({"error": "object_reads_unsupported", "retryable": False}, True)
            if fault == "verify_failure" and args["key"] == "A" and self.creations:
                return text({"error": "verification_unavailable", "retryable": False}, True)
            return text({"objects": [obj for obj in self.objects.values() if obj["key"] == args["key"]]})
        if name == "create":
            self.creations += 1
            obj = {"id": f"created-{self.creations}", **deepcopy(args), "version": 1}
            self.objects[obj["id"]] = obj
            if fault == "create_timeout":
                return text({"error": "timeout", "outcome": "unknown"}, True)
            return text({"id": obj["id"]})
        if name == "update":
            if fault == "deny_B" and self.phase == 1:
                return text({"error": "permission_denied", "retryable": False, "effect": "not_executed"}, True)
            obj = self.objects.get(args["id"])
            if not obj:
                return text({"error": "not_found", "retryable": False}, True)
            if fault == "concurrent_edit" and "edited" not in self.flags:
                self.flags.add("edited")
                obj["content"] += "\nCollaborator addition"
                obj["properties"]["collaborator"] = "keep"
                obj["relations"].append("R-other")
                obj["version"] += 1
                return text({"error": "conflict", "retryable": False, "effect": "not_executed", "message": "Another user changed this object after your read. Read it again and reassess."}, True)
            if args.get("expected_version", obj["version"]) != obj["version"]:
                return text({"error": "conflict", "retryable": False, "effect": "not_executed"}, True)
            obj["content"] = args["content"]
            obj["properties"].update(args["properties"])
            obj["relations"] = deepcopy(args["relations"])
            obj["version"] += 1
            return text({"id": obj["id"]})
        if name == "checkpoint":
            if args["key"] not in self.checkpoints:
                self.checkpoints.append(args["key"])
            return text({"complete": self.checkpoints})
        if name == "delete":
            self.objects.pop(args["id"], None)
            return text({"deleted": args["id"]})
        return text({"error": "unknown_tool"}, True)


def resume(fixture, trace):
    fixture.phase = 2
    return {"phase": 2}


def stop(fixture, trace):
    before = fixture.snapshot()
    fixture.stopped = True
    result = {"stopped": True}
    append(trace, {"name": "__user_stop__", "arguments": {}, "phase": fixture.phase,
                   "before": before, "after": fixture.snapshot(), "result": text(result)})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--trace", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"))
    serve(Fixture(next(case for case in cases if case["id"] == args.case)), args.trace, "relay-write-fixture",
          {"fixture/resume": resume, "fixture/stop": stop})
