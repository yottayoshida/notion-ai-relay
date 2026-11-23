from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import warnings

from scripts.check_structure import check_eval_cases, frontmatter, load_yaml, stage, validate


REPOSITORY = Path(__file__).resolve().parents[1]


def run_check_structure(*arguments):
    # Not strict, for the same reason as _support.run.
    return subprocess.run([sys.executable, str(REPOSITORY / "scripts/check_structure.py"), *map(str, arguments)],
                          capture_output=True, encoding="utf-8", errors="backslashreplace")


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "notion-ai-relay"
        self.root.mkdir()
        stage(REPOSITORY, self.root)

    def skill(self, metadata, body=""):
        _, original_body = frontmatter((REPOSITORY / "SKILL.md").read_text(encoding="utf-8"))
        (self.root / "SKILL.md").write_text("---\n" + metadata + "\n---\n" + original_body + "\n" + body, encoding="utf-8")

    def append_link(self, link):
        with (self.root / "SKILL.md").open("a", encoding="utf-8") as stream:
            stream.write("\n" + link + "\n")

    def test_current_distribution(self):
        markdowns, yamls, links = validate(self.root)
        self.assertGreaterEqual(markdowns, 6)
        self.assertGreaterEqual(yamls, 1)
        self.assertGreater(links, 0)

    def test_invalid_frontmatter(self):
        cases = [
            ("name: [", "YAML"),
            ("name: notion-ai-relay", "description"),
            ("name: Notion-AI-Relay\ndescription: test", "name"),
            ("name: notion--ai-relay\ndescription: test", "name"),
            ("name: -notion-ai-relay\ndescription: test", "name"),
            ("name: notion-ai-relay-\ndescription: test", "name"),
            ("name: " + "a" * 65 + "\ndescription: test", "name"),
            ("name: 42\ndescription: test", "name"),
            ("name: notion-ai-relay\ndescription: ''", "description"),
            ("name: notion-ai-relay\ndescription: " + "x" * 1025, "description"),
            ("name: notion-ai-relay\ndescription: test\ncompatibility: " + "x" * 501, "compatibility"),
            ("name: notion-ai-relay\ndescription: test\nmetadata: {version: 1}", "metadata"),
            ("name: notion-ai-relay\ndescription: test\nname: other", "duplicate YAML key"),
        ]
        for metadata, message in cases:
            with self.subTest(metadata=metadata[:80]):
                self.skill(metadata)
                if message == "YAML":
                    import yaml
                    with self.assertRaises(yaml.YAMLError):
                        validate(self.root)
                else:
                    with self.assertRaisesRegex(ValueError, message):
                        validate(self.root)

    def test_frontmatter_delimiters_and_mapping_required(self):
        for text in ("name: test", "---\nname: test", "---\n- test\n---"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                frontmatter(text)

    def test_valid_boundary_lengths_and_optional_fields(self):
        self.skill("name: notion-ai-relay\ndescription: " + "x" * 1024
                   + "\ncompatibility: " + "x" * 500
                   + '\nlicense: MIT\nallowed-tools: Read\nmetadata: {version: "1"}')
        validate(self.root)

    def test_valid_name_boundaries_and_unicode(self):
        config = (REPOSITORY / "agents/openai.yaml").read_text(encoding="utf-8")
        for name in ("a", "a" * 64, "中文", "café"):
            with self.subTest(name=name):
                renamed = self.root.with_name(name)
                self.root.rename(renamed)
                self.root = renamed
                self.skill(f"name: {name}\ndescription: test")
                (self.root / "agents/openai.yaml").write_text(config.replace("$notion-ai-relay", "$" + name), encoding="utf-8")
                validate(self.root)

    def test_folder_mismatch_and_missing_required_file(self):
        renamed = self.root.with_name("notion-ai-relay-main")
        self.root.rename(renamed)
        with self.assertRaisesRegex(ValueError, "does not match folder"):
            validate(renamed)
        renamed.rename(self.root)
        (self.root / "references/read-skills.md").unlink()
        with self.assertRaisesRegex(ValueError, "missing required file"):
            validate(self.root)

    def test_broken_links_anchors_images_and_reference_links(self):
        for link, message in [
            ("[missing](references/missing.md)", "missing local reference"),
            ("[anchor](references/read-skills.md#missing)", "missing anchor"),
            ("![icon](assets/missing.png)", "missing local reference"),
            ("[guide][ref]\n\n[ref]: references/missing.md", "missing local reference"),
            ("[escape](../outside.md)", "escapes Skill directory"),
        ]:
            with self.subTest(link=link):
                self.skill("name: notion-ai-relay\ndescription: test", link)
                with self.assertRaisesRegex(ValueError, message):
                    validate(self.root)

    def test_valid_anchor_variants_and_external_links(self):
        (self.root / "references/space name.md").write_text(
            '# Repeated `title`!\n# Repeated `title`!\n<a id="explicit"></a>\n', encoding="utf-8")
        self.skill("name: notion-ai-relay\ndescription: test", """# Local heading
[local](#local-heading)
[encoded](references/space%20name.md#repeated-title-1)
[explicit](references/space%20name.md#explicit)
[external](https://example.invalid/not-checked#missing)
`[code](missing.md)`

```markdown
[example](missing.md)
```
""")
        validate(self.root)

    def test_invalid_display_metadata_and_skill_reference(self):
        path = self.root / "agents/openai.yaml"
        original = path.read_text(encoding="utf-8")
        for text, message in [
            ("interface: []", "interface metadata"),
            (original.replace('"Notion AI Relay"', "42"), "display_name"),
            (original.replace("Run Notion agents and skills through MCP", "short"), "25-64"),
            (original.replace("$notion-ai-relay", "$other"), "reference"),
            (original.replace("$notion-ai-relay", "$notion-ai-relay-other"), "reference"),
            (original + '  icon_small: "./missing.png"\n', "missing local reference"),
            (original + '  icon_small: "https://example.invalid/icon.png"\n', "local asset"),
            (original + '  icon_small: ""\n', "local asset"),
            (original + '  brand_color: 123\n', "hex color"),
        ]:
            with self.subTest(message=message):
                path.write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    validate(self.root)

    def test_valid_icon_asset_and_brand_color(self):
        (self.root / "assets").mkdir()
        (self.root / "assets/icon.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        with (self.root / "agents/openai.yaml").open("a", encoding="utf-8") as stream:
            stream.write('  icon_small: "./assets/icon.svg"\n  brand_color: "#1a2b3c"\n')
        validate(self.root)

    def test_cli_rejects_malformed_metadata_yaml(self):
        (self.root / "agents/openai.yaml").write_text("interface: [報告", encoding="utf-8")
        result = run_check_structure("--skill-dir", self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL", result.stderr)
        self.assertNotIn("PASS", result.stdout)

    def test_unknown_frontmatter_field_is_rejected(self):
        self.skill("name: notion-ai-relay\ndescription: test\nunexpected: value")
        with self.assertRaisesRegex(ValueError, "unexpected frontmatter"):
            validate(self.root)

    def test_codex_default_prompt_only_asks_for_the_list(self):
        interface = load_yaml((REPOSITORY / "agents/openai.yaml").read_text(encoding="utf-8"))["interface"]
        self.assertEqual(interface["default_prompt"],
                         "$notion-ai-relay List the Notion Custom Agents and Notion Skills I can access.")

    def test_html_in_code_does_not_create_an_anchor(self):
        self.append_link('`<a id="not-an-anchor"></a>`\n\n[broken](#not-an-anchor)')
        with self.assertRaisesRegex(ValueError, "missing anchor"):
            validate(self.root)

    def test_codex_string_values_must_be_quoted(self):
        path = self.root / "agents/openai.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace('"Notion AI Relay"', 'Notion AI Relay'), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "quoted"):
            validate(self.root)

    def test_yaml_duplicate_keys_are_not_silently_overwritten(self):
        with self.assertRaisesRegex(ValueError, "duplicate YAML key"):
            load_yaml("interface: {}\ninterface: {}")

    def test_staged_distribution_is_every_file_git_would_ship(self):
        source = Path(self.temp.name) / "source"
        (source / "tests/topic").mkdir(parents=True)
        (source / ".venv").mkdir()
        for name, text in {
            "SKILL.md": "x", "tests/topic/README.md": "x", "gone.md": "x",
            ".gitignore": ".venv/\n", ".venv/ignored.md": "x", "new.md": "x",
            "tests/topic/metadata.json": "{}",
        }.items():
            (source / name).write_text(text, encoding="utf-8")
        git = ["git", "-C", str(source)]
        subprocess.run(git + ["init", "-q"], check=True)
        subprocess.run(git + ["add", "SKILL.md", "tests/topic/README.md", "gone.md", ".gitignore", "tests/topic/metadata.json"], check=True)
        (source / "gone.md").unlink()
        destination = Path(self.temp.name) / "staged"
        destination.mkdir()
        stage(source, destination)
        staged = {str(path.relative_to(destination)) for path in destination.rglob("*") if path.is_file()}
        self.assertEqual(staged, {"SKILL.md", "tests/topic/README.md", ".gitignore", "new.md"})

    def test_staging_outside_git_fails(self):
        source = Path(self.temp.name) / "not-a-repository"
        source.mkdir()
        with self.assertRaises(ValueError):
            stage(source, self.root)

    def test_cli_staging_success_and_installed_fixture_failure(self):
        result = run_check_structure()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("structure only", result.stdout)
        self.append_link("[broken](references/missing.md)")
        result = run_check_structure("--skill-dir", self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing local reference", result.stderr)
        self.assertNotIn("PASS", result.stdout)


class EvalCaseTests(unittest.TestCase):
    def test_every_eval_folder_holds_cases_with_a_unique_id_and_an_expected_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            stage(REPOSITORY, Path(directory))
            self.assertGreaterEqual(check_eval_cases(Path(directory)), 1)

    def test_eval_cases_without_an_id_or_an_expected_outcome_fail(self):
        for name, text, message in [
            ("no-id", '[{"expected": "x"}]', "missing or duplicate id"),
            ("no-expected", '[{"id": "a"}]', "no expected outcome"),
            ("blank-expected", '[{"id": "a", "expected": "   "}]', "no expected outcome"),
            ("no-cases", '[]', "no cases"),
            ("no-cases-key", '{"version": 1}', "no cases"),
            ("cases-not-a-list", '{"cases": {"id": "a"}}', "no cases"),
            ("case-not-an-object", '["a"]', "not an object"),
            ("null-case", '[null]', "not an object"),
            ("empty-expected", '[{"id": "a", "expected": {}}]', "no expected outcome"),
            ("all-expectations-empty", '{"cases": [{"id": "a", "expected_status": "", "expected_operations": []}]}', "no expected outcome"),
            ("duplicate-id", '[{"id": "a", "expected": "x"}, {"id": "a", "expected": "y"}]', "duplicate id"),
            ("broken-json", "{", "Expecting"),
            ("no-cases-file", None, "missing cases.json"),
        ]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory) / "evals" / "topic"
                folder.mkdir(parents=True)
                if text is not None:
                    (folder / "cases.json").write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    check_eval_cases(Path(directory))

    def test_a_case_whose_only_expectation_is_false_or_zero_still_has_one(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "evals" / "topic"
            folder.mkdir(parents=True)
            (folder / "cases.json").write_text('[{"id": "a", "expected": false}, {"id": "b", "expected_count": 0}]', encoding="utf-8")
            self.assertEqual(check_eval_cases(Path(directory)), 1)

    def test_validate_rejects_a_distribution_with_a_bad_eval_case(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "notion-ai-relay"
            root.mkdir()
            stage(REPOSITORY, root)
            validate(root)
            (root / "evals/discovery/cases.json").write_text('[{"id": "a"}]', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no expected outcome"):
                validate(root)


class SuiteWarningTests(unittest.TestCase):
    def test_deprecation_warnings_stay_visible_in_the_suite_run(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.warn("synthetic deprecation", DeprecationWarning)
        self.assertEqual([str(warning.message) for warning in caught], ["synthetic deprecation"])


if __name__ == "__main__":
    unittest.main()
