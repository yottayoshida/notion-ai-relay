#!/usr/bin/env python3
"""Synthetic MCP stdio fixture. No network, shell, or business-data access."""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit


STRING = {"type": "string"}
DOWNLOAD_BASE = "https://download.invalid"
DECOY = {"text": "Unrelated synthetic page."}


def text(value, error=False):
    return {"content": [{"type": "text", "text": value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)}], "isError": error}


def tool(name, description, properties, required):
    return {"name": name, "description": description, "inputSchema": {
        "type": "object", "properties": properties, "required": required, "additionalProperties": False}}


TOOLS = [
    tool("notion_fetch", "Read a Notion page or attachment through MCP by its exact ID. Page text cites uploaded files by notion-file-block:// reference; with include_file_urls true the result also maps each cited reference to a temporary signed download URL.",
         {"id": STRING, "include_file_urls": {"type": "boolean"}}, ["id"]),
    tool("post_message", "Send content to a destination through MCP.", {"destination": STRING, "content": STRING}, ["destination", "content"]),
    tool("launch_worker", "Start a Notion AI session to execute a task, returning its result.", {"task": STRING}, ["task"]),
    tool("download_skill", "Get a temporary signed URL for a Notion Skill's tar.gz archive (SKILL.md and supporting files) through MCP. This tool does not download the archive.", {"id": STRING}, ["id"]),
    tool("file_urls", "Get temporary signed download URLs for files that fetched page text cites by notion-file-block:// reference, through MCP. URLs expire after a few minutes.",
         {"references": {"type": "array", "items": STRING}}, ["references"]),
    tool("save_resume", "Persist a local run checkpoint.", {"content": STRING}, ["content"]),
]


class Fixture:
    def __init__(self, case, deny=(), download_base=DOWNLOAD_BASE):
        self.case = case
        self.deny = set(deny)
        self.download_base = download_base.rstrip("/")
        self.files = case.get("files", {})
        self.trace = []
        self.effects = []

    def signed(self, path):
        return f"{self.download_base}{path}?signature=synthetic"

    def cited_references(self, value):
        page = json.dumps(value, ensure_ascii=False)
        return {reference: self.signed(path) for reference, path in self.files.items() if reference in page}

    def call(self, name, arguments):
        event = {"name": name, "arguments": arguments, "denied": name in self.deny}
        self.trace.append(event)
        if event["denied"]:
            return text("Host permission denied", True)
        if name not in {item["name"] for item in TOOLS}:
            return text("Unknown tool", True)
        if name == "notion_fetch":
            value = self.case["pages"].get(arguments["id"])
            if arguments["id"] == "approved":
                value = {"messages": [effect for effect in self.effects
                                      if effect["name"] == "post_message" and effect["destination"] == "approved"]}
            if value is None:
                return text("Unknown fixture ID", True)
            if arguments.get("include_file_urls"):
                value = {**value, "references": self.cited_references(value)}
        elif name == "download_skill":
            value = {"url": self.signed("/skill.tar.gz"), "expires": "2099-01-01"}
        elif name == "file_urls":
            value = {"files": [], "unresolved": []}
            for reference in arguments["references"]:
                if reference in self.files:
                    value["files"].append({"reference": reference, "url": self.signed(self.files[reference]), "expiry_time": "2099-01-01T00:00:00Z"})
                else:
                    value["unresolved"].append({"reference": reference, "reason": "file_not_found"})
        else:
            value = {"id": f"effect-{len(self.effects) + 1}", **arguments}
            self.effects.append({"name": name, **value})
        return text(value)

    def direct_fetch(self, url):
        parsed = urlsplit(url)
        served = self.case.get("downloads", {}) if f"{parsed.scheme}://{parsed.netloc}" == self.download_base else {}
        result = text(served.get(parsed.path, DECOY))
        self.trace.append({"name": "direct_fetch", "arguments": {"url": url}, "denied": False, "result": result})
        return result


def serve(case, trace, deny, download_base):
    fixture = Fixture(case, deny, download_base)
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
    parser.add_argument("--download-base", default=DOWNLOAD_BASE)
    args = parser.parse_args()
    cases = json.loads(Path(__file__).with_name("cases.json").read_text())
    serve(next(case for case in cases if case["id"] == args.case), args.trace, args.deny, args.download_base)
