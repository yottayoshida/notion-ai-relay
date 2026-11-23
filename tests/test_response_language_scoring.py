import json
from pathlib import Path
import tempfile
import unittest

from _support import load, run

ROOT = Path(__file__).parent / "response-language"
scorer = load("response-language", "score")
CASES = {case["id"]: case for case in json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))}


def judgment(output, languages=None, total=10):
    return {"output_sha256": scorer.output_digest(output), "format_ok": True,
            "meaning_ok": True, "total": total, "languages": languages or {}}


def grade(case_id, output, languages=None, **kwargs):
    return scorer.score(CASES[case_id], output, judgment(output, languages), **kwargs)


def json_output(**changes):
    value = {"status": "ok", "source_id": "fixture-03", "total": 10, "summary": "The total is 10."}
    value.update(changes)
    return json.dumps(value)


POST_REPLY = {"post": "English", "reply": "Japanese"}
EXAMPLES = {
    "japanese-request": ("合計は10です。", {"reply": "Japanese"}),
    "explicit-english": ("The total is 10.", {"reply": "English"}),
    "json-only": (json_output(), {}),
    "delegated-french": ("合計は10です。", {"reply": "Japanese"}),
    "destination-language-required": (
        "POST\n- Shipped onboarding email v2; fixed login timeout.\nREPLY\n投稿内容を確認しました。", POST_REPLY),
    "destination-language-unstated": (
        "POST\n- Shipped onboarding email v2; fixed login timeout.\nREPLY\n投稿内容を確認しました。", POST_REPLY),
    "returned-required-language": (
        "DRAFT\nDear Acme Paper, we confirm delivery on November 20, 2026.",
        {"draft": "English"}),
}


class ResponseLanguageScoringTests(unittest.TestCase):
    def test_valid_outputs_cover_all_seven_cases(self):
        self.assertEqual(set(EXAMPLES), set(CASES))
        for case_id, (output, languages) in EXAMPLES.items():
            with self.subTest(case=case_id):
                result = grade(case_id, output, languages)
                self.assertTrue(result["passed"], result)

    def test_correct_alternative_wording_and_block_markup_are_accepted(self):
        self.assertTrue(grade("japanese-request", "合計は十です。", {"reply": "Japanese"})["passed"])
        self.assertTrue(grade("explicit-english", "The total is ten.", {"reply": "English"})["passed"])
        output = "## **POST:**\r\nCompleted both tasks.\r\n## REPLY\r\n投稿内容を確認しました。\r\n"
        self.assertTrue(grade("destination-language-unstated", output,
                              {"post": "English", "reply": "Japanese"})["passed"])

    def test_post_preamble_is_allowed_and_its_language_is_judged_separately(self):
        body = "POST\nBoth tasks completed.\nREPLY\n投稿内容を確認しました。"
        for preamble, language, expected_pass in (
            ("以下が投稿案と返信案です。", "Japanese", True),
            ("Here are the proposed post and reply.", "English", False),
        ):
            with self.subTest(language=language):
                output = preamble + "\n\n" + body
                languages = {"post": "English", "reply": "Japanese", "preamble": language}
                result = grade("destination-language-unstated", output, languages)
                self.assertTrue(result["automated_checks_passed"], result)
                self.assertEqual(result["passed"], expected_pass, result)
        output = "以下が投稿案と返信案です。\n\n" + body
        self.assertFalse(grade("destination-language-unstated", output,
                               {"post": "English", "reply": "Japanese"})["passed"])

    def test_output_only_json_and_draft_still_reject_preambles(self):
        outputs = {
            "json-only": '{"status":"ok","source_id":"fixture-03","total":10,"summary":"Total 10"}',
            "returned-required-language": "DRAFT\nDear Acme Paper, delivery is confirmed for November 20, 2026.",
        }
        for case_id, body in outputs.items():
            with self.subTest(case=case_id):
                result = grade(case_id, "以下が結果です。\n" + body,
                               {"draft": "English", "preamble": "Japanese"})
                self.assertFalse(result["automated_checks_passed"])
                self.assertFalse(result["passed"])

    def test_delegated_french_result_is_not_a_japanese_reply(self):
        result = grade("delegated-french", "Le total est de 10.", {"reply": "French"})
        self.assertFalse(result["passed"])
        self.assertIn("wrong or unreviewed reply language: expected Japanese", result["errors"])

    def test_post_and_reply_languages_are_scored_independently(self):
        for case_id in ("destination-language-required", "destination-language-unstated"):
            for output, languages, wrong_role in (
                ("POST\n両方のタスクが完了しました。\nREPLY\n投稿内容を確認しました。",
                 {"post": "Japanese", "reply": "Japanese"}, "post"),
                ("POST\nBoth tasks completed.\nREPLY\nHere is the planned post.",
                 {"post": "English", "reply": "English"}, "reply"),
            ):
                with self.subTest(case=case_id, wrong_role=wrong_role):
                    result = grade(case_id, output, languages)
                    self.assertFalse(result["passed"])
                    self.assertTrue(any(f"{wrong_role} language" in error for error in result["errors"]))

    def test_required_draft_language_and_optional_note_are_separate(self):
        output = "DRAFT\nDear Acme Paper, delivery is confirmed for November 20, 2026.\nNOTE\n送信していません。"
        self.assertTrue(grade("returned-required-language", output,
                              {"draft": "English", "note": "Japanese"})["passed"])
        wrong_outputs = (
            ("DRAFT\nAcme Paper 様、2026年11月20日の納品を確認します。\nNOTE\n送信していません。",
             {"draft": "Japanese", "note": "Japanese"}),
            ("DRAFT\nDear Acme Paper, delivery is confirmed for November 20, 2026.\nNOTE\nNot sent.",
             {"draft": "English", "note": "English"}),
        )
        for output, languages in wrong_outputs:
            self.assertFalse(grade("returned-required-language", output, languages)["passed"])

    def test_json_language_is_unrestricted_but_schema_and_values_are_not(self):
        value = {"status": "ok", "source_id": "fixture-03", "total": 10, "summary": "The total is 10."}
        for summary in ("The total is 10.", "合計は10です。", "Le total est de 10."):
            output = json.dumps({**value, "summary": summary}, ensure_ascii=False)
            self.assertTrue(grade("json-only", output)["passed"])
        wrong_outputs = [
            json.dumps({**value, "source_id": "translated-id"}),
            json.dumps({**value, "status": "成功"}),
            json.dumps({**value, "total": 6}),
            json.dumps({**value, "summary": None}),
            json.dumps({**value, "extra": "comment"}),
            json.dumps({"状態": "ok", "source_id": "fixture-03", "total": 10, "summary": "total"}),
            '```json\n' + json.dumps(value) + '\n```',
            '{"status":"ok","status":"ok","source_id":"fixture-03","total":10,"summary":"Total 10"}',
            '{"status":',
        ]
        for output in wrong_outputs:
            with self.subTest(output=output):
                result = grade("json-only", output)
                self.assertFalse(result["automated_checks_passed"])
                self.assertFalse(result["passed"])

    def test_json_total_comparison_preserves_exact_numeric_values(self):
        for literal, expected_pass in (
            ("10", True), ("10.0", True), ("1e1", True),
            ("10.0000000000000001", False),
            ("9.9999999999999999", False),
            ("1.00000000000000001e1", False),
            ("1e999999999999999999999999", False),
        ):
            with self.subTest(total=literal):
                output = ('{"status":"ok","source_id":"fixture-03","total":'
                          + literal + ',"summary":"The total is 10."}')
                result = grade("json-only", output)
                self.assertEqual(result["automated_checks_passed"], expected_pass, result)
                self.assertEqual(result["passed"], expected_pass, result)

    def test_format_checks_alone_or_stale_judgment_cannot_pass_a_case(self):
        output = "合計は10です。"
        result = scorer.score(CASES["japanese-request"], output)
        self.assertTrue(result["automated_checks_passed"])
        self.assertFalse(result["passed"])
        stale = judgment("The total is 10.", {"reply": "Japanese"})
        result = scorer.score(CASES["japanese-request"], output, stale)
        self.assertIn("semantic assessment is not bound to this output", result["errors"])

    def test_incorrect_total_meaning_or_unconfirmed_format_cannot_pass(self):
        output = "合計は6です。"
        for change in ({"total": 6}, {"meaning_ok": False}, {"format_ok": False}, {"languages": {}}):
            with self.subTest(change=change):
                assessment = {**judgment(output, {"reply": "Japanese"}), **change}
                self.assertFalse(scorer.score(CASES["japanese-request"], output, assessment)["passed"])

    def test_missing_duplicate_or_empty_blocks_are_not_complete_outputs(self):
        for output in ("POST\nDraft only", "POST\n\nREPLY\n説明", "POST\nA\nPOST\nB\nREPLY\n説明"):
            with self.subTest(output=output):
                self.assertFalse(grade("destination-language-required", output,
                                       {"post": "English", "reply": "Japanese"})["automated_checks_passed"])

    def test_incomplete_runs_fail_even_with_valid_output_and_judgment(self):
        self.assertFalse(grade("japanese-request", "合計は10です。", {"reply": "Japanese"}, completed=False)["passed"])

    def test_cli_exit_status_distinguishes_valid_wrong_language_and_pending_review(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "output.txt"
            assessment_path = Path(directory) / "judgment.json"
            for case_id, output, languages, assessed, expected_exit in (
                ("japanese-request", "合計は10です。", {"reply": "Japanese"}, True, 0),
                ("delegated-french", "Le total est de 10.", {"reply": "French"}, True, 1),
                ("japanese-request", "合計は10です。", {}, False, 1),
                ("json-only", '{"status":', {}, True, 1),
                ("json-only", '{"status":"ok","source_id":"fixture-03","total":10.0000000000000001,"summary":"Total 10"}', {}, True, 1),
                ("json-only", '{"status":"ok","source_id":"fixture-03","total":1e1,"summary":"Total 10"}', {}, True, 0),
                ("destination-language-unstated",
                 "投稿案と返信案です。\nPOST\nShipped onboarding email v2; fixed login timeout.\nREPLY\n投稿内容を確認しました。",
                 {"preamble": "Japanese", "post": "English", "reply": "Japanese"}, True, 0),
                ("destination-language-unstated",
                 "Here are the post and reply.\nPOST\nShipped onboarding email v2; fixed login timeout.\nREPLY\n投稿内容を確認しました。",
                 {"preamble": "English", "post": "English", "reply": "Japanese"}, True, 1),
            ):
                with self.subTest(case=case_id, assessed=assessed):
                    output_path.write_bytes(output.encode("utf-8"))
                    assessment_path.write_text(json.dumps(judgment(output, languages)), encoding="utf-8")
                    arguments = [case_id, output_path] + (["--assessment", assessment_path] if assessed else [])
                    result = run("response-language", "score.py", arguments)
                    self.assertEqual(result.returncode, expected_exit, result.stderr)
                    report = json.loads(result.stdout)
                    self.assertEqual(report["passed"], expected_exit == 0)


UNREVIEWED = object()


def row(label, case_id, expected, output=None, languages=None, assessment=UNREVIEWED, completed=True, **review):
    valid_output, valid_languages = EXAMPLES[case_id]
    output = valid_output if output is None else output
    if assessment is UNREVIEWED:
        assessment = judgment(output, valid_languages if languages is None else languages)
        assessment.update(review)
    return label, (CASES[case_id], output, assessment), {"completed": completed}, expected


VALID_JSON_LENGTH = len(json_output())
ONE_FAULT_ROWS = [
    *[row(f"valid {case_id}", case_id, []) for case_id in EXAMPLES],
    row("JSON total written as 10.0", "json-only", [], output=json_output(total=10.0)),
    row("JSON total written as 1e1", "json-only", [], output='{"status":"ok","source_id":"fixture-03","total":1e1,"summary":"Total 10"}'),
    row("post with a preamble in the reply language", "destination-language-required", [],
        output="以下が投稿案です。\nPOST\nShipped.\nREPLY\n確認しました。", languages={**POST_REPLY, "preamble": "Japanese"}),
    row("draft with a Japanese note", "returned-required-language", [],
        output="DRAFT\nDear Acme Paper, delivery is confirmed.\nNOTE\n送付前に日付を確認してください。",
        languages={"draft": "English", "note": "Japanese"}),
    row("incomplete run", "japanese-request", ["missing or incomplete output"], completed=False),
    row("no labeled blocks", "destination-language-required", ["expected labeled output blocks"], output="Shipped. 確認しました。"),
    row("POST block twice", "destination-language-required", ["duplicate block: post"],
        output="POST\nShipped.\nPOST\nAgain.\nREPLY\n確認しました。"),
    row("empty POST block", "destination-language-required", ["empty block: post"], output="POST\n\nREPLY\n確認しました。"),
    row("REPLY block missing", "destination-language-required", ["expected POST and REPLY blocks"], output="POST\nShipped."),
    row("DRAFT block missing", "returned-required-language", ["expected DRAFT and optional NOTE blocks"], output="NOTE\n送付前に確認。"),
    row("extra block beside DRAFT", "returned-required-language", ["expected DRAFT and optional NOTE blocks"],
        output="DRAFT\nDear Acme Paper.\nPOST\nShipped."),
    row("JSON key repeated", "json-only", ["duplicate JSON key: status"],
        output='{"status":"ok","status":"ok","source_id":"fixture-03","total":10,"summary":"Total 10"}'),
    row("JSON with commentary", "json-only", [f"Extra data: line 1 column {VALID_JSON_LENGTH + 2} (char {VALID_JSON_LENGTH + 1})"],
        output=json_output() + " Done."),
    row("JSON key missing", "json-only", ["incorrect JSON keys"],
        output=json.dumps({"status": "ok", "source_id": "fixture-03", "total": 10})),
    row("JSON status changed", "json-only", ["incorrect JSON value: status"], output=json_output(status="done")),
    row("JSON source changed", "json-only", ["incorrect JSON value: source_id"], output=json_output(source_id="fixture-04")),
    row("JSON total changed", "json-only", ["incorrect JSON value: total"], output=json_output(total=11)),
    row("JSON total off by a tiny fraction", "json-only", ["incorrect JSON value: total"],
        output='{"status":"ok","source_id":"fixture-03","total":10.0000000000000001,"summary":"Total 10"}'),
    row("JSON summary empty", "json-only", ["summary must be nonempty text"], output=json_output(summary=" ")),
    row("no semantic review", "japanese-request", ["semantic assessment required; format checks alone are not a case PASS"],
        assessment=None),
    row("review of another output", "japanese-request", ["semantic assessment is not bound to this output"], output_sha256="0" * 64),
    row("format not confirmed", "japanese-request", ["format not semantically confirmed"], format_ok=False),
    row("meaning not confirmed", "japanese-request", ["meaning not semantically confirmed"], meaning_ok=False),
    row("French example total copied", "delegated-french", ["incorrect or unreviewed total"], total=6),
    row("reply in the wrong language", "japanese-request", ["wrong or unreviewed reply language: expected Japanese"],
        languages={"reply": "English"}),
    row("post in the wrong language", "destination-language-required", ["wrong or unreviewed post language: expected English"],
        languages={**POST_REPLY, "post": "Japanese"}),
    row("preamble in the wrong language", "destination-language-required",
        ["wrong or unreviewed preamble language: expected Japanese"],
        output="Here are the drafts.\nPOST\nShipped.\nREPLY\n確認しました。", languages={**POST_REPLY, "preamble": "English"}),
    row("draft in the wrong language", "returned-required-language", ["wrong or unreviewed draft language: expected English"],
        languages={"draft": "Japanese"}),
    row("note in the wrong language", "returned-required-language", ["wrong or unreviewed note language: expected Japanese"],
        output="DRAFT\nDear Acme Paper.\nNOTE\nCheck the date.", languages={"draft": "English", "note": "English"}),
]


if __name__ == "__main__":
    unittest.main()
