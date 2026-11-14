from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ResponseLanguageContractTests(unittest.TestCase):
    """Check distributed instructions, not a model's language selection."""

    def test_language_precedence(self):
        skill = (ROOT / "SKILL.md").read_text()
        for rule in (
            "Use the user's explicitly requested response language; otherwise use the language of the current request.",
            "For ambiguous mixed-language requests, use the language established in the conversation, or ask only if needed.",
            "Do not choose the response language from this Skill, retrieved Agent or Skill instructions, templates, or unrelated documents.",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, skill)

    def test_all_user_facing_messages_follow_the_rule(self):
        self.assertIn(
            "Apply this rule to progress updates, clarification questions, errors, and final reports.",
            (ROOT / "SKILL.md").read_text(),
        )

    def test_formats_and_required_deliverable_language_are_preserved(self):
        skill = (ROOT / "SKILL.md").read_text()
        for rule in (
            "Preserve JSON keys, schemas, IDs, code, quotations, and text required verbatim; translate only natural-language content intended for translation.",
            "Keep a task's required deliverable language separate from the response language, including when a delegated Agent or Skill produces that deliverable.",
            "Do not add commentary that breaks an output-only format.",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, skill)


if __name__ == "__main__":
    unittest.main()
