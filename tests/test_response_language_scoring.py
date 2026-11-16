import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parent / "response-language"
SPEC = importlib.util.spec_from_file_location("response_language_score", ROOT / "score.py")
scorer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scorer)
CASES = {case["id"]: case for case in json.loads((ROOT / "cases.json").read_text())}


def judgment(output, languages=None, total=10):
    return {"output_sha256": scorer.output_digest(output), "format_ok": True,
            "meaning_ok": True, "total": total, "languages": languages or {}}


def grade(case_id, output, languages=None, **kwargs):
    return scorer.score(CASES[case_id], output, judgment(output, languages), **kwargs)


class ResponseLanguageScoringTests(unittest.TestCase):
    def test_valid_outputs_cover_all_seven_cases(self):
        examples = {
            "japanese-request": ("合計は10です。", {"reply": "Japanese"}),
            "explicit-english": ("The total is 10.", {"reply": "English"}),
            "json-only": (json.dumps({"status": "ok", "source_id": "fixture-03", "total": 10,
                                      "summary": "The total is 10."}), {}),
            "delegated-french": ("合計は10です。", {"reply": "Japanese"}),
            "destination-language-required": (
                "POST\n- Shipped onboarding email v2; fixed login timeout.\nREPLY\n投稿内容を確認しました。",
                {"post": "English", "reply": "Japanese"}),
            "destination-language-unstated": (
                "POST\n- Shipped onboarding email v2; fixed login timeout.\nREPLY\n投稿内容を確認しました。",
                {"post": "English", "reply": "Japanese"}),
            "returned-required-language": (
                "DRAFT\nDear Acme Paper, we confirm delivery on November 20, 2026.",
                {"draft": "English"}),
        }
        self.assertEqual(set(examples), set(CASES))
        for case_id, (output, languages) in examples.items():
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
                ("destination-language-unstated",
                 "投稿案と返信案です。\nPOST\nShipped onboarding email v2; fixed login timeout.\nREPLY\n投稿内容を確認しました。",
                 {"preamble": "Japanese", "post": "English", "reply": "Japanese"}, True, 0),
                ("destination-language-unstated",
                 "Here are the post and reply.\nPOST\nShipped onboarding email v2; fixed login timeout.\nREPLY\n投稿内容を確認しました。",
                 {"preamble": "English", "post": "English", "reply": "Japanese"}, True, 1),
            ):
                with self.subTest(case=case_id, assessed=assessed):
                    output_path.write_bytes(output.encode("utf-8"))
                    assessment_path.write_text(json.dumps(judgment(output, languages)))
                    command = [sys.executable, "-B", str(ROOT / "score.py"), case_id, str(output_path)]
                    if assessed:
                        command += ["--assessment", str(assessment_path)]
                    result = subprocess.run(command, text=True, capture_output=True, timeout=5)
                    self.assertEqual(result.returncode, expected_exit, result.stderr)
                    report = json.loads(result.stdout)
                    self.assertEqual(report["passed"], expected_exit == 0)


if __name__ == "__main__":
    unittest.main()
