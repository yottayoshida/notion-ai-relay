import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DiscoveryContractTests(unittest.TestCase):
    """Static instruction checks, not model-behavior or MCP compatibility tests."""

    def test_default_prompt_requests_only_discovery(self):
        metadata = (ROOT / "agents/openai.yaml").read_text()
        prompt_line = next(
            line for line in metadata.splitlines()
            if line.strip().startswith("default_prompt:")
        )
        prompt = json.loads(prompt_line.split(":", 1)[1].strip())
        self.assertEqual(
            prompt,
            "$notion-ai-relay List the Notion Custom Agents and Notion Skills I can access.",
        )

    def test_discovery_does_not_reuse_a_previous_selection(self):
        skill = (ROOT / "SKILL.md").read_text()
        self.assertIn(
            "A target selected earlier in the conversation does not turn a discovery request into an execution request.",
            skill,
        )
        self.assertIn(
            "Return the list without first requiring a target selection or executing any listed item.",
            skill,
        )

    def test_explicit_execution_remains_supported(self):
        skill = (ROOT / "SKILL.md").read_text()
        self.assertIn(
            'Treat "carry out" and "run" as requests to execute, not merely explain the configuration.',
            skill,
        )
        self.assertIn(
            "For execution requests, identify the target type, name or URL, task, input, and execution or dry-run mode.",
            skill,
        )

    def test_execution_example_is_separate_from_codex_default(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn("The Codex default prompt requests discovery only.", readme)
        self.assertIn("Carry out this Custom Agent's task.\nAgent URL:", readme)
        self.assertIn("Input: <target page, time period, and other required input>", readme)


if __name__ == "__main__":
    unittest.main()
