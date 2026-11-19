import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

TESTS = Path(__file__).resolve().parent


def load(suite, name):
    path = TESTS / suite / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{suite.replace('-', '_')}_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    return module


def cases_of(suite):
    value = json.loads((TESTS / suite / "cases.json").read_text())
    return value["cases"] if isinstance(value, dict) else value


def case_with_id(cases, case_id):
    return next(case for case in cases if case["id"] == case_id)


def run(suite, script, arguments, stdin=""):
    return subprocess.run([sys.executable, str(TESTS / suite / script), *map(str, arguments)],
                          input=stdin, text=True, capture_output=True, timeout=5)


def stdio(suite, arguments, requests):
    result = run(suite, "mock_mcp.py", arguments,
                 "".join(json.dumps({"jsonrpc": "2.0", **request}) + "\n" for request in requests))
    return result, [json.loads(line) for line in result.stdout.splitlines()]


def scorer_cli(score, script, description, first_report=False):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("case")
    parser.add_argument("trace", type=Path)
    parser.add_argument("final", type=Path)
    if first_report:
        parser.add_argument("--first-report", type=Path)
    parser.add_argument("--incomplete", action="store_true")
    args = parser.parse_args()
    case = case_with_id(json.loads(Path(script).with_name("cases.json").read_text()), args.case)
    trace = [json.loads(line) for line in args.trace.read_text().splitlines()]
    options = {"first_report": args.first_report.read_text() if args.first_report else None} if first_report else {}
    result = score(case, trace, args.final.read_text(), not args.incomplete, **options)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
