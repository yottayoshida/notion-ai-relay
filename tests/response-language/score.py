"""Fixture format checks plus explicit, output-bound semantic judgments; no model calls."""
import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re


HEADINGS = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]+)?(?P<mark>\*\*|__)?(?P<role>POST|REPLY|DRAFT|NOTE)"
    r"[ \t]*[:：]?(?(mark)(?P=mark))[ \t]*[:：]?[ \t]*\r?$",
    re.IGNORECASE | re.MULTILINE)


def output_digest(output):
    return hashlib.sha256(output.encode("utf-8")).hexdigest()


def blocks(output):
    matches = list(HEADINGS.finditer(output))
    result = {}
    if not matches:
        raise ValueError("expected labeled output blocks")
    preamble = output[:matches[0].start()].strip()
    if preamble:
        result["preamble"] = preamble
    for index, match in enumerate(matches):
        role = match["role"].lower()
        if role in result:
            raise ValueError(f"duplicate block: {role}")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(output)
        result[role] = output[match.end():end].strip()
        if not result[role]:
            raise ValueError(f"empty block: {role}")
    return result


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def score(case, output, assessment=None, completed=True):
    expected = case["expected"]
    errors = []
    if not completed or not output.strip():
        errors.append("missing or incomplete output")
    languages = {}
    if "keys" in expected:
        try:
            value = json.loads(output, object_pairs_hook=unique_object, parse_float=Decimal)
            if not isinstance(value, dict) or set(value) != set(expected["keys"]):
                raise ValueError("incorrect JSON keys")
            for key in ("status", "source_id", "total"):
                if value[key] != expected[key]:
                    raise ValueError(f"incorrect JSON value: {key}")
            if not isinstance(value["summary"], str) or not value["summary"].strip():
                raise ValueError("summary must be nonempty text")
        except (ValueError, InvalidOperation) as error:
            errors.append(str(error))
    elif "post_language" in expected or "draft_language" in expected:
        try:
            parts = blocks(output)
            if "post_language" in expected:
                if set(parts) - {"preamble"} != {"post", "reply"}:
                    raise ValueError("expected POST and REPLY blocks")
                languages = {"post": expected["post_language"], "reply": expected["reply_language"]}
                if "preamble" in parts:
                    languages["preamble"] = expected["reply_language"]
            else:
                if "draft" not in parts or not set(parts).issubset({"draft", "note"}):
                    raise ValueError("expected DRAFT and optional NOTE blocks")
                languages = {"draft": expected["draft_language"]}
                if "note" in parts:
                    languages["note"] = "Japanese"
        except ValueError as error:
            errors.append(str(error))
    else:
        languages = {"reply": expected["response_language"]}
    automated_ok = not errors
    if not isinstance(assessment, dict):
        errors.append("semantic assessment required; format checks alone are not a case PASS")
    else:
        if assessment.get("output_sha256") != output_digest(output):
            errors.append("semantic assessment is not bound to this output")
        if assessment.get("format_ok") is not True:
            errors.append("format not semantically confirmed")
        if assessment.get("meaning_ok") is not True:
            errors.append("meaning not semantically confirmed")
        if "total" in expected and "keys" not in expected and assessment.get("total") != expected["total"]:
            errors.append("incorrect or unreviewed total")
        observed = assessment.get("languages", {})
        if not isinstance(observed, dict):
            observed = {}
        for role, language in languages.items():
            if str(observed.get(role, "")).casefold() != language.casefold():
                errors.append(f"wrong or unreviewed {role} language: expected {language}")
    return {"case": case["id"], "passed": not errors,
            "automated_checks_passed": automated_ok, "errors": errors,
            "required_language_judgments": languages,
            "output_sha256": output_digest(output)}


def main():
    cases = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=[case["id"] for case in cases])
    parser.add_argument("output", type=Path)
    parser.add_argument("--assessment", type=Path)
    parser.add_argument("--incomplete", action="store_true")
    args = parser.parse_args()
    case = next(case for case in cases if case["id"] == args.case)
    assessment = json.loads(args.assessment.read_text(encoding="utf-8")) if args.assessment else None
    output = args.output.read_bytes().decode("utf-8")
    result = score(case, output, assessment, completed=not args.incomplete)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
