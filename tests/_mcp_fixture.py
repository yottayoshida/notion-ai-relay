import json
import sys

STRING = {"type": "string"}
TYPES = {"string": str, "integer": int, "boolean": bool, "object": dict, "array": list}


def tool(name, description, properties, required):
    return {"name": name, "description": description, "inputSchema": {
        "type": "object", "properties": properties, "required": required, "additionalProperties": False}}


def text(value, error=False):
    body = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return {"content": [{"type": "text", "text": body}], "isError": error}


def schema_error(schema, value, path="arguments"):
    expected = schema.get("type")
    if expected == "integer":
        # bool is a subclass of int; without this exclusion `true` passes as an integer.
        if isinstance(value, bool) or not (isinstance(value, int) or (isinstance(value, float) and value.is_integer())):
            return f"{path} must be integer"
    elif expected and not isinstance(value, TYPES[expected]):
        return f"{path} must be {expected}"
    if "enum" in schema and value not in schema["enum"]:
        return f"{path} must be one of {schema['enum']}"
    if expected == "integer" and not schema.get("minimum", value) <= value <= schema.get("maximum", value):
        return f"{path} is out of range"
    if expected == "array":
        for index, item in enumerate(value):
            if error := schema_error(schema.get("items", {}), item, f"{path}[{index}]"):
                return error
    if expected == "object":
        properties = schema.get("properties", {})
        missing = [key for key in schema.get("required", []) if key not in value]
        if missing:
            return f"{path} is missing {', '.join(missing)}"
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                error = schema_error(properties[key], item, f"{path}.{key}")
            elif extra is False:
                error = f"{path} has unexpected {key}"
            else:
                error = schema_error(extra, item, f"{path}.{key}") if isinstance(extra, dict) else None
            if error:
                return error
    return None


def as_declared(schema, value):
    if schema.get("type") == "integer" and isinstance(value, float):
        return int(value)
    if schema.get("type") == "array" and isinstance(value, list):
        return [as_declared(schema.get("items", {}), item) for item in value]
    if schema.get("type") == "object" and isinstance(value, dict):
        properties, extra = schema.get("properties", {}), schema.get("additionalProperties")
        return {key: as_declared(properties.get(key, extra if isinstance(extra, dict) else {}), item) for key, item in value.items()}
    return value


def checked(tools, name, arguments, dispatch):
    schema = next((item["inputSchema"] for item in tools if item["name"] == name), None)
    if schema is None:
        return dispatch(arguments)
    if error := schema_error(schema, arguments):
        return text({"error": "invalid_arguments", "message": error}, True)
    try:
        return dispatch(as_declared(schema, arguments))
    except Exception as failure:
        return text({"error": "fixture_error", "message": f"{type(failure).__name__}: {failure}"}, True)


def tool_error(call):
    result = call.get("result") or {}
    try:
        return json.loads(result["content"][0]["text"]).get("error") if result.get("isError") else None
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        return None


def split_rejected(calls):
    rejected = [tool_error(call) == "invalid_arguments" for call in calls]
    return ([call for call, flag in zip(calls, rejected) if not flag],
            [call for call, flag in zip(calls, rejected) if flag])


def append(trace, record):
    with trace.open("a", encoding="utf-8") as out:
        out.write(json.dumps(record) + "\n")


def use_utf8_stdio():
    # Not the locale's encoding: clients send UTF-8 JSON, which fails to decode under Shift JIS.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")


def serve(fixture, trace, server_name, extra_methods=None):
    extra_methods = extra_methods or {}
    use_utf8_stdio()
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        method = request["method"]
        if method == "initialize":
            result = {"protocolVersion": request["params"]["protocolVersion"], "capabilities": {"tools": {}},
                      "serverInfo": {"name": server_name, "version": "1"}}
        elif method == "tools/list":
            result = {"tools": fixture.tools()}
        elif method == "tools/call":
            params = request.get("params") or {}
            name, arguments = params.get("name"), params.get("arguments", {})
            if isinstance(name, str):
                result = fixture.call(name, arguments)
                append(trace, fixture.calls[-1])
            else:
                result = text({"error": "invalid_arguments", "message": "name must be string"}, True)
                append(trace, {"name": name, "arguments": arguments, "result": result})
        elif method == "ping":
            result = {}
        elif method in extra_methods:
            result = extra_methods[method](fixture, trace)
        else:
            print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "error": {"code": -32601, "message": "Unknown method"}}), flush=True)
            continue
        print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
