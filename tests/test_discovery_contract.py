import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DiscoveryContractTests(unittest.TestCase):
    def test_codex_default_prompt_only_asks_for_the_list(self):
        metadata = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        prompt_line = next(
            line for line in metadata.splitlines()
            if line.strip().startswith("default_prompt:")
        )
        prompt = json.loads(prompt_line.split(":", 1)[1].strip())
        self.assertEqual(
            prompt,
            "$notion-ai-relay List the Notion Custom Agents and Notion Skills I can access.",
        )


if __name__ == "__main__":
    unittest.main()
