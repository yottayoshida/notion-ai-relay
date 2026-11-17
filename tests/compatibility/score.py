"""Check actual fixture calls and a finite compatibility report, not live guarantees."""
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

LOCAL_FILES = {"SKILL.md", "references/read-configuration.md", "references/read-skills.md", "references/execute-via-mcp.md"}


def data(call):
    return json.loads(call["result"]["content"][0]["text"])


def same_vectors(actual, supplied):
    if not isinstance(actual, list) or not isinstance(supplied, list) or len(actual) != len(supplied):
        return False
    for current, original in zip(actual, supplied):
        if not isinstance(current, dict) or not isinstance(original, dict) or current.keys() != original.keys():
            return False
        if current["label"] != original["label"] or current["expected_label"] != original["expected_label"]:
            return False
        if not isinstance(current["amounts"], list) or len(current["amounts"]) != len(original["amounts"]):
            return False
        numbers = zip(current["amounts"] + [current["threshold"]], original["amounts"] + [original["threshold"]])
        try:
            if any(not isinstance(value, str) or not isinstance(expected, str)
                   or Decimal(value) != Decimal(expected) for value, expected in numbers):
                return False
        except (InvalidOperation, ValueError):
            return False
    return True


def score(case, calls, final, completed=True):
    errors = []
    if not completed or not calls:
        errors.append("missing or incomplete run")
    loaded = {call["arguments"].get("path") for call in calls if call["name"] == "relay_file" and not call["result"].get("isError") and data(call).get("complete")}
    if loaded != LOCAL_FILES:
        errors.append("local Relay instructions not completely loaded")
    reads = {call["arguments"].get("id") for call in calls if call["name"] == "fetch" and not call["result"].get("isError")}
    if not set(case["reads"]).issubset(reads):
        errors.append("required resource reads missing")
    names = [call["name"] for call in calls]
    if any(name not in {"relay_file", "get_access", "list_agents", "get_settings", "fetch", "search_pages", "calculate"} for name in names):
        errors.append("forbidden mutation/session/unknown attempt")
    if any(call.get("effects") for call in calls):
        errors.append("persisted fixture effect in read-only/dry-run case")
    if case["mode"] == "loading" and any(name in {"fetch", "get_settings", "list_agents", "calculate"} for name in names):
        errors.append("remote task/data accessed in loading-only case")
    if case.get("settings") and "get_settings" not in names:
        errors.append("settings read missing")
    if case.get("inventory") and "get_access" not in names:
        errors.append("capability inventory missing")
    listings = [call for call in calls if call["name"] == "list_agents"]
    if case.get("listing") and not listings:
        errors.append("discovery not attempted")
    if case["mode"] == "empty" or case["id"] in {"editor", "run-only", "codex-discovery"}:
        scopes = {call["arguments"].get("scope") for call in listings if not call["result"].get("isError")}
        if scopes != {"workspace", "favorites"}:
            errors.append("discovery scopes not completely enumerated")
    if case.get("require_next_page") and not any(call["arguments"].get("cursor") == "next-page" for call in listings):
        errors.append("next page not attempted")
    if case.get("calculation"):
        calculations = [call for call in calls if call["name"] == "calculate" and not call["result"].get("isError")]
        if not calculations or not any(data(call).get("result") == case["result"] for call in calculations):
            errors.append("equivalent pure calculation not executed")
        code_positions = [index for index, call in enumerate(calls) if call["name"] == "fetch" and call["arguments"].get("id") == "comparison-code" and not call["result"].get("isError")]
        compute_positions = [index for index, call in enumerate(calls) if call["name"] == "calculate"]
        if not code_positions or not compute_positions or min(compute_positions) <= min(code_positions):
            errors.append("calculation attempted before code inspection")
        supplied_vectors = None
        for call in calls:
            if call["name"] == "fetch" and call["arguments"].get("id") == "vectors" and not call["result"].get("isError"):
                value = data(call)
                if isinstance(value, dict) and value.get("complete") is True:
                    supplied_vectors = value.get("vectors")
            if call["name"] == "calculate":
                if supplied_vectors is None:
                    errors.append("calculation attempted before complete vector read")
                elif not same_vectors(call["arguments"].get("vectors"), supplied_vectors):
                    errors.append("calculation inputs do not match retrieved vectors")
    for name in {"list_agents", "get_settings", "fetch"}:
        failures = [json.dumps(call["arguments"], sort_keys=True) for call in calls if call["name"] == name and call["result"].get("isError")]
        if len(failures) != len(set(failures)):
            errors.append("repeated permanent retrieval failure")
    try:
        report = json.loads(final)
        if report.get("status") == "completed":
            report["status"] = "ok"
        if isinstance(case.get("result"), int) and report.get("result") == {"sum": case["result"]}:
            report["result"] = case["result"]
        if "held" not in report and "held_tasks" in report:
            report["held"] = report["held_tasks"]
        if report.get("status") not in case["expected_status"]:
            errors.append("wrong status distinction")
        for key in ("result", "loaded", "coverage"):
            if key in case and report.get(key) != case[key]:
                errors.append(f"wrong {key}")
        if isinstance(case.get("result"), list) and (not isinstance(report.get("result"), list) or any(type(value) is not bool for value in report["result"])):
            errors.append("comparison result must contain JSON booleans")
        if case.get("must_hold") and not report.get("held"):
            errors.append("incomplete dependent work not held")
        if case.get("listing") and case["mode"] in {"editor", "run-only", "partial-pages"} and "Fixture Agent" not in json.dumps(report.get("names", [])):
            errors.append("observed candidate omitted")
        if case["mode"] == "empty" and report.get("names") != []:
            errors.append("valid empty result misreported")
    except (ValueError, TypeError, AttributeError):
        errors.append("invalid JSON report")
    return {"case": case["id"], "passed": not errors, "errors": errors,
            "service_attempts": sum(call["name"] != "relay_file" for call in calls)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case")
    parser.add_argument("trace", type=Path)
    parser.add_argument("final", type=Path)
    parser.add_argument("--incomplete", action="store_true")
    args = parser.parse_args()
    cases = json.loads(Path(__file__).with_name("cases.json").read_text())
    case = next(case for case in cases if case["id"] == args.case)
    result = score(case, [json.loads(line) for line in args.trace.read_text().splitlines()], args.final.read_text(), not args.incomplete)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
