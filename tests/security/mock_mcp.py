#!/usr/bin/env python3
"""Synthetic MCP stdio fixture. No network, shell, or business-data access."""
import argparse
import json
from pathlib import Path
import sys


def tool(name, description, properties, required):
    return {"name": name, "description": description, "inputSchema": {
        "type": "object", "properties": {key: {"type": "string"} for key in properties},
        "required": required, "additionalProperties": False}}


TOOLS = [
    tool("notion_fetch", "Read a Notion page or attachment through MCP by its exact ID.", ["id"], ["id"]),
    tool("post_message", "Send content to a destination through MCP.", ["destination", "content"], ["destination", "content"]),
    tool("launch_worker", "Start a Notion AI session to execute a task, returning its result.", ["task"], ["task"]),
    tool("download_skill", "Get temporary signed archive URL metadata through MCP; does not download the archive.", ["id"], ["id"]),
    tool("save_resume", "Persist a local run checkpoint.", ["content"], ["content"]),
]


class Fixture:
    def __init__(self, case, deny=()):
        self.case = case
        self.deny = set(deny)
        self.trace = []
        self.effects = []

    def call(self, name, arguments):
        event = {"name": name, "arguments": arguments, "denied": name in self.deny}
        self.trace.append(event)
        if event["denied"]:
            return {"content": [{"type": "text", "text": "Host permission denied"}], "isError": True}
        if name not in {item["name"] for item in TOOLS}:
            return {"content": [{"type": "text", "text": "Unknown tool"}], "isError": True}
        if name == "notion_fetch":
            value = self.case["pages"].get(arguments["id"])
            if arguments["id"] == "approved":
                value = {"messages": [effect for effect in self.effects
                                      if effect["name"] == "post_message" and effect["destination"] == "approved"]}
            if value is None:
                return {"content": [{"type": "text", "text": "Unknown fixture ID"}], "isError": True}
        elif name == "download_skill":
            value = {"url": "https://download.invalid/archive?signature=synthetic", "expires": "2099-01-01"}
        else:
            value = {"id": f"effect-{len(self.effects) + 1}", **arguments}
            self.effects.append({"name": name, **value})
        return {"content": [{"type": "text", "text": json.dumps(value)}], "isError": False}


def serve(case, trace, deny):
    fixture = Fixture(case, deny)
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        method = request["method"]
        if method == "initialize":
            result = {"protocolVersion": request["params"]["protocolVersion"],
                      "capabilities": {"tools": {}}, "serverInfo": {"name": "relay-security-fixture", "version": "1"}}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = request["params"]
            result = fixture.call(params["name"], params.get("arguments", {}))
            with trace.open("a") as out:
                out.write(json.dumps({**fixture.trace[-1], "result": result}) + "\n")
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
    parser.add_argument("--deny", action="append", default=[])
    args = parser.parse_args()
    cases = json.loads(Path(__file__).with_name("cases.json").read_text())
    serve(next(case for case in cases if case["id"] == args.case), args.trace, args.deny)
