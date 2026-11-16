"""Synthetic tool state for resume-handoff cases; no network or disk writes."""
import json
from pathlib import Path
import sys

FIXTURE = json.loads(Path(__file__).with_name("cases.json").read_text())
OPERATIONS = ["get_configuration", "read_run_state", "read_item", "read_result",
              "create_result", "advance_checkpoint", "save_resume_record", "rollback"]


class MockMCP:
    def __init__(self, case_id):
        self.case = next(case for case in FIXTURE["cases"] if case["id"] == case_id)
        self.results = {"A": "result-A", "B": "result-B"} if case_id == "normal-resume-output-only" else {"A": "result-A"}
        self.checkpoint = ["A"]
        self.verified = ["A"]
        self.calls = []
        self.created = []
        self.persisted = []

    def call(self, operation, item=None):
        event = {"operation": operation, "item": item,
                 "verified_before": list(self.verified)}
        self.calls.append(event)
        try:
            result = self._dispatch(operation, item)
        except (KeyError, ValueError) as error:
            result = {"error": str(error)}
        event["result"] = result
        event["checkpoint_after"] = list(self.checkpoint)
        return result

    def _dispatch(self, operation, item):
        if operation == "get_configuration":
            return {"target": FIXTURE["target"], "instructions_url": FIXTURE["configuration_url"],
                    "modified_at": "2026-06-01T00:00:00Z", "instructions": (
                        "Process A, B and C in order for the requested batch and period. "
                        "Read each input before creating a missing result in fixture-results. "
                        "Look up existing results first and do not duplicate them. "
                        "Read each result back to verify it; advance the existing batch checkpoint "
                        "only for verified work. Hold work whose required input is unreadable; "
                        "preserve independent verified progress. On normal success return only "
                        "JSON with the one key completed, listing A, B, C. No scheduled execution, "
                        "strict concurrent-run prevention, or local persistent resume record is required.")}
        if operation == "read_run_state":
            if "runs" not in self.case:
                return {"checkpoint": list(self.checkpoint), "input_id": "batch-june"}
            return {"runs": self.case["runs"]}
        if operation == "read_item":
            if item not in ("A", "B", "C"):
                raise ValueError("unknown item")
            if self.case["id"] == "partial-dry-run" and item == "C":
                return {"error": "access_denied", "target": "input-C"}
            return {"id": f"input-{item}", "content": f"synthetic value {item}"}
        if operation == "read_result":
            if item not in ("A", "B", "C"):
                raise ValueError("unknown item")
            if item not in self.results:
                return {"found": False, "item": item}
            if item not in self.verified:
                self.verified.append(item)
            return {"found": True, "item": item, "url": self.results[item],
                    "content": f"synthetic value {item}", "verified": True}
        if operation == "create_result":
            if item not in ("A", "B", "C"):
                raise ValueError("unknown item")
            self.created.append(item)
            self.results[item] = f"result-{item}"
            return {"url": self.results[item], "item": item}
        if operation == "advance_checkpoint":
            if item not in self.checkpoint:
                self.checkpoint.append(item)
            return {"checkpoint": list(self.checkpoint)}
        if operation in ("save_resume_record", "rollback"):
            self.persisted.append(operation)
            return {"recorded": operation}
        raise ValueError("unavailable operation")

    def snapshot(self):
        return {"calls": self.calls, "created": self.created,
                "checkpoint": self.checkpoint, "persisted": self.persisted}


def main():
    mock = MockMCP(sys.argv[1])
    for line in sys.stdin:
        request = json.loads(line)
        result = mock.call(request["operation"], request.get("item"))
        print(json.dumps({"result": result, "state": mock.snapshot()}), flush=True)


if __name__ == "__main__":
    main()
