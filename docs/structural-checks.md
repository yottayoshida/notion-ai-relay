# Structural checks

Use Python 3.10 or newer in an isolated environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
sh scripts/check.sh
```

The same command runs on pull requests. It tests invalid fixtures and checks a temporary distribution folder named `notion-ai-relay`, independently of the checkout's name. The staged files are every file git tracks, plus new files that git's ignore rules do not exclude, without `metadata.json`, because `npx skills add` installs the whole repository except `metadata.json`. Run it from a git checkout. To check an installed copy instead, run `python3 scripts/check_structure.py --skill-dir /path/to/notion-ai-relay` from the development environment.

Checks cover YAML syntax (including duplicate keys), required files, [Agent Skills frontmatter constraints](https://agentskills.io/specification), folder/name agreement, local Markdown links and heading anchors, and the display fields and Skill reference in [Codex metadata](https://github.com/openai/skills/blob/main/skills/.system/skill-creator/references/openai_yaml.md). The Codex display fields are optional in the general format but required by this repository's distribution check. Codex string values must be quoted and keys unquoted. The usefulness of descriptions still needs review. External URLs are not fetched. Use Markdown links for local resources; code examples and bare paths are not checked as references.

**A structural PASS is not a model-execution or Notion-compatibility PASS.** It does not prove that a client loads the Skill, that an assistant follows the instructions, or that MCP access is available. GitHub-hosted CI execution must be confirmed separately from a local run.
