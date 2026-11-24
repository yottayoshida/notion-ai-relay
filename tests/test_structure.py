import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings

import yaml

from scripts.check_structure import check_eval_cases, frontmatter, load_yaml, stage, validate


REPOSITORY = Path(__file__).resolve().parents[1]
REQUIRED = ("SKILL.md", "README.md", "LICENSE", "agents/openai.yaml", "references/read-configuration.md",
            "references/read-skills.md", "references/execute-via-mcp.md", "docs/agent-retrieval.md")


def run_check_structure(*arguments, cwd=None):
    # Not strict, for the same reason as _support.run.
    return subprocess.run([sys.executable, str(REPOSITORY / "scripts/check_structure.py"), *map(str, arguments)],
                          capture_output=True, encoding="utf-8", errors="backslashreplace", cwd=cwd)


MINIMAL_CODEX = """interface:
  display_name: "Relay"
  short_description: "Run Notion agents through MCP clients"
  default_prompt: "$notion-ai-relay List agents."
"""


def minimal_skill(path, body):
    for relative in REQUIRED:
        (path / relative).parent.mkdir(parents=True, exist_ok=True)
        (path / relative).write_text("text\n", encoding="utf-8")
    (path / "SKILL.md").write_text("---\nname: notion-ai-relay\ndescription: test\n---\n" + body, encoding="utf-8")
    (path / "agents/openai.yaml").write_text(MINIMAL_CODEX, encoding="utf-8")
    return path


def staged(path):
    path.mkdir(parents=True)
    stage(REPOSITORY, path)
    return path


def checkout(staged_copy, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    staged_copy.rename(path)
    subprocess.run(["git", "-C", str(path), "init", "-q"], check=True)
    (path / ".venv/lib").mkdir(parents=True)
    (path / ".venv/lib/port.yaml").write_text("- a list, not a mapping\n", encoding="utf-8")
    (path / ".claude").mkdir()
    (path / ".claude/notes.md").write_text("[draft](missing.md)\n", encoding="utf-8")
    return path


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = staged(Path(self.temp.name) / "notion-ai-relay")

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

    def test_invalid_frontmatter_is_named_exactly(self):
        name = "invalid frontmatter name"
        cases = [
            ("name: notion-ai-relay", "invalid frontmatter description: expected 1-1024 characters"),
            ("name: Notion-AI-Relay\ndescription: test", name),
            ("name: notion--ai-relay\ndescription: test", name),
            ("name: -notion-ai-relay\ndescription: test", name),
            ("name: notion-ai-relay-\ndescription: test", name),
            ("name: " + "a" * 65 + "\ndescription: test", name),
            ("name: ''\ndescription: test", name),
            ("name: notion_ai_relay\ndescription: test", name),
            ("name: notion.ai\ndescription: test", name),
            ("name: 42\ndescription: test", name),
            ("name: notion-ai-relay\ndescription: ''", "invalid frontmatter description: expected 1-1024 characters"),
            ("name: notion-ai-relay\ndescription: " + "x" * 1025, "invalid frontmatter description: expected 1-1024 characters"),
            ("name: notion-ai-relay\ndescription: test\ncompatibility: " + "x" * 501,
             "invalid frontmatter compatibility: expected 1-500 characters"),
            ("name: notion-ai-relay\ndescription: test\nmetadata: {version: 1}", "frontmatter metadata must map strings to strings"),
            ("name: notion-ai-relay\ndescription: test\nlicense: 1", "frontmatter license must be a string"),
            ("name: notion-ai-relay\ndescription: test\nallowed-tools: [Read]", "frontmatter allowed-tools must be a string"),
            ("name: notion-ai-relay\ndescription: test\nname: other", "duplicate YAML key: name"),
            ("name: notion-ai-relay\ndescription: test\nmetadata: x", "frontmatter metadata must map strings to strings"),
            ("name: notion-ai-relay\ndescription: test\nmetadata: {1: x}", "frontmatter metadata must map strings to strings"),
        ]
        for metadata, message in cases:
            with self.subTest(metadata=metadata[:80]):
                self.skill(metadata)
                with self.assertRaises(ValueError) as caught:
                    validate(self.root)
                self.assertEqual(str(caught.exception), "SKILL.md: " + message)

    def test_frontmatter_yaml_syntax_error_names_the_file(self):
        self.skill("name: [")
        with self.assertRaises(ValueError) as caught:
            validate(self.root)
        self.assertTrue(str(caught.exception).startswith("SKILL.md: "), caught.exception)
        self.assertIsInstance(caught.exception.__cause__, yaml.YAMLError)

    def test_skill_without_frontmatter_delimiters_fails(self):
        (self.root / "SKILL.md").write_text("name: notion-ai-relay\n", encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            validate(self.root)
        self.assertEqual(str(caught.exception), "SKILL.md: missing YAML frontmatter delimiters")

    def test_frontmatter_delimiters_and_mapping_required(self):
        for text, message in [
            ("", "missing YAML frontmatter delimiters"),
            ("name: test", "missing YAML frontmatter delimiters"),
            ("name: test\n---\nbody", "missing YAML frontmatter delimiters"),
            ("---\nname: test", "missing YAML frontmatter delimiters"),
            ("---\n- test\n---", "expected a YAML mapping"),
            ("---\n---\nbody", "expected a YAML mapping"),
        ]:
            with self.subTest(text=text), self.assertRaises(ValueError) as caught:
                frontmatter(text)
            self.assertEqual(str(caught.exception), message)

    def test_the_line_after_the_frontmatter_is_part_of_the_body(self):
        self.assertEqual(frontmatter("---\nname: test\n---\n[first](missing.md)\nrest"),
                         ({"name": "test"}, "[first](missing.md)\nrest"))

    def test_every_required_file_is_reported_when_missing(self):
        for relative in REQUIRED:
            with self.subTest(relative=relative):
                (self.root / relative).unlink()
                with self.assertRaises(ValueError) as caught:
                    validate(self.root)
                self.assertEqual(str(caught.exception), f"missing required file: {relative}")
                shutil.copy2(REPOSITORY / relative, self.root / relative)

    def test_validate_counts_local_links_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = minimal_skill(Path(directory) / "notion-ai-relay",
                                 "[local](README.md)\n[license](LICENSE)\n[external](https://example.invalid/x)\n[mail](mailto:a@example.invalid)\n"
                                 "[relative to protocol](//example.invalid/x)\n<a href>no target</a>\n")
            self.assertEqual(validate(root), (6, 1, 2))
            result = run_check_structure("--skill-dir", root)
            self.assertEqual((result.returncode, result.stdout),
                             (0, "PASS: 6 Markdown files, 1 YAML files, 2 local references; structure only\n"), result.stderr)

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

    def test_every_read_or_parse_failure_names_its_file(self):
        for relative, content, message in [
            (".github/broken.yml", b"a: [", None),
            (".github/list.yml", b"- a", "expected a YAML mapping"),
            (".github/duplicate.yml", b"a: 1\na: 2", "duplicate YAML key: a"),
            (".github/latin1.yml", b"a: \xff", None),
            ("docs/latin1.md", b"\xff", None),
            ("evals/discovery/cases.json", b"{", None),
        ]:
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes() if path.exists() else None
                path.write_bytes(content)
                with self.assertRaises(ValueError) as caught:
                    validate(self.root)
                self.assertTrue(str(caught.exception).startswith(relative + ": "), caught.exception)
                if message:
                    self.assertEqual(str(caught.exception), f"{relative}: {message}")
                if original is None:
                    path.unlink()
                else:
                    path.write_bytes(original)

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

    def test_html_links_are_checked_like_markdown_links(self):
        (self.root / "assets").mkdir()
        (self.root / "assets/icon.png").write_bytes(b"png")
        for html, message in [
            ('<a href="references/missing.md">x</a>', "missing local reference: references/missing.md"),
            ('<img src="assets/missing.png">', "missing local reference: assets/missing.png"),
            ('<p><img src="assets/missing.png"/></p>', "missing local reference: assets/missing.png"),
            ('<a href="references/read-skills.md#missing">x</a>', "missing anchor: references/read-skills.md#missing"),
            ('<img src="assets/icon.png#gh-dark-mode-only">', "cannot validate anchor in non-Markdown file: assets/icon.png#gh-dark-mode-only"),
            ('<a href="../outside.md">x</a>', "local reference escapes Skill directory: ../outside.md"),
        ]:
            with self.subTest(html=html):
                self.skill("name: notion-ai-relay\ndescription: test", html)
                with self.assertRaises(ValueError) as caught:
                    validate(self.root)
                self.assertEqual(str(caught.exception), "SKILL.md: " + message)

    def test_valid_html_links_directory_links_and_html_in_code_pass(self):
        (self.root / "assets").mkdir()
        (self.root / "assets/icon.png").write_bytes(b"png")
        self.skill("name: notion-ai-relay\ndescription: test", """[evals](evals/)
[tests](tests)
<a href="references/read-skills.md#read-instructions-and-supporting-resources">ok</a>
<img src="assets/icon.png" alt="Relay icon">
<a href="https://example.invalid/not-checked">external</a>
<a href>no target</a>
<span href="missing.md">not a link</span>
<source src="missing.mp4">
`<a href="missing.md">code</a>`
""")
        validate(self.root)

    def test_only_a_name_and_any_id_make_an_html_anchor(self):
        self.append_link('<a name="named">x</a> <span id="spanned">y</span>\n\n[n](#named) [s](#spanned)')
        validate(self.root)
        for html, anchor in [('<input name="field">', "field"), ('<a class="styled">x</a>', "styled")]:
            with self.subTest(html=html):
                self.skill("name: notion-ai-relay\ndescription: test", f"{html}\n\n[link](#{anchor})")
                with self.assertRaisesRegex(ValueError, f"missing anchor: #{anchor}"):
                    validate(self.root)

    def test_a_directory_with_an_anchor_cannot_be_validated(self):
        self.append_link("[evals](evals/#cases)")
        with self.assertRaisesRegex(ValueError, "cannot validate anchor in non-Markdown file: evals/#cases"):
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
        short = "Run Notion agents and skills through MCP"
        for text, message in [
            ("interface: []", "openai.yaml requires interface metadata"),
            (original.replace('"Notion AI Relay"', "42"), "openai.yaml requires interface.display_name"),
            (original.replace('"Notion AI Relay"', '"   "'), "openai.yaml requires interface.display_name"),
            (original.replace(f'  short_description: "{short}"\n', ""), "openai.yaml requires interface.short_description"),
            (original.replace(short, "x" * 24), "openai.yaml short_description must be 25-64 characters"),
            (original.replace(short, "x" * 65), "openai.yaml short_description must be 25-64 characters"),
            ("\n".join(line for line in original.splitlines() if "default_prompt" not in line) + "\n",
             "openai.yaml requires interface.default_prompt"),
            (original.replace("$notion-ai-relay", "$other"), "openai.yaml default_prompt must reference $notion-ai-relay"),
            (original.replace("$notion-ai-relay", "$notion-ai-relay-other"), "openai.yaml default_prompt must reference $notion-ai-relay"),
            (original + '  icon_small: "./missing.png"\n', "missing local reference: ./missing.png"),
            (original + '  icon_large: "./missing.png"\n', "missing local reference: ./missing.png"),
            (original + '  icon_small: "https://example.invalid/icon.png"\n', "openai.yaml icon_small must reference a local asset"),
            (original + '  icon_small: ""\n', "openai.yaml icon_small must reference a local asset"),
            (original + '  icon_small: 5\n', "openai.yaml icon_small must reference a local asset"),
            (original + '  brand_color: 123\n', "openai.yaml brand_color must be a hex color"),
            (original + '  brand_color: "red"\n', "openai.yaml brand_color must be a hex color"),
            (original.replace("  display_name:", '  "display_name":'), "openai.yaml keys must be unquoted"),
        ]:
            with self.subTest(message=message, text=text[-40:]):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError) as caught:
                    validate(self.root)
                self.assertEqual(str(caught.exception), "agents/openai.yaml: " + message)

    def test_display_metadata_boundaries_and_quoting_that_pass(self):
        path = self.root / "agents/openai.yaml"
        original = path.read_text(encoding="utf-8")
        for text in [original.replace("Run Notion agents and skills through MCP", "x" * 25),
                     original.replace("Run Notion agents and skills through MCP", "x" * 64),
                     original.replace('"Notion AI Relay"', "'Notion AI Relay'"),
                     original + "  count: 3\n"]:
            with self.subTest(text=text[-40:]):
                path.write_text(text, encoding="utf-8")
                validate(self.root)

    def test_icon_must_be_a_file_not_a_directory(self):
        with (self.root / "agents/openai.yaml").open("a", encoding="utf-8") as stream:
            stream.write('  icon_small: "./evals"\n')
        with self.assertRaises(ValueError) as caught:
            validate(self.root)
        self.assertEqual(str(caught.exception), "agents/openai.yaml: openai.yaml icon_small must reference a local asset")

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

    def test_cli_skill_dir_dot_checks_the_current_folder(self):
        result = run_check_structure("--skill-dir", ".", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_cli_skill_dir_checks_only_what_a_checkout_would_install(self):
        root = checkout(self.root, Path(self.temp.name) / "checkout" / "notion-ai-relay")
        for arguments, cwd in [((".",), root), (("../notion-ai-relay",), root)]:
            with self.subTest(arguments=arguments):
                result = run_check_structure("--skill-dir", *arguments, cwd=cwd)
                self.assertEqual(result.returncode, 0, result.stderr)
        renamed = root.with_name("notion-ai-relay-main")
        root.rename(renamed)
        result = run_check_structure("--skill-dir", ".", cwd=renamed)
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not match folder 'notion-ai-relay-main'", result.stderr)

    def test_cli_skill_dir_through_a_symlink_keeps_the_installed_name(self):
        real = checkout(self.root, Path(self.temp.name) / "real-checkout")
        link = Path(self.temp.name) / "linked" / "notion-ai-relay"
        link.parent.mkdir()
        os.symlink(real, link, target_is_directory=True)
        result = run_check_structure("--skill-dir", link)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_skill_dir_inside_another_repository_checks_the_folder_itself(self):
        project = Path(self.temp.name) / "project"
        skill = project / ".claude/skills/notion-ai-relay"
        skill.parent.mkdir(parents=True)
        self.root.rename(skill)
        (project / ".gitignore").write_text(".claude/\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(project), "init", "-q"], check=True)
        result = run_check_structure("--skill-dir", skill)
        self.assertEqual(result.returncode, 0, result.stderr)
        shutil.rmtree(skill / "references")
        result = run_check_structure("--skill-dir", skill)
        self.assertIn("missing required file", result.stderr)

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
            ("numeric-id", '[{"id": 5, "expected": "x"}]', "missing or duplicate id 5"),
            ("empty-id", '[{"id": "", "expected": "x"}]', "missing or duplicate id ''"),
            ("null-expected", '[{"id": "a", "expected": null}]', "no expected outcome"),
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
