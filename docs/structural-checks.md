# Structural checks

Use Python 3.10 or newer in an isolated environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
sh scripts/check.sh
```

The same command runs on pull requests, on Python 3.10 and 3.15 and on Python 3.12 under a Shift JIS locale (`ja_JP.SJIS`). It makes Python's warning for a file or process opened without an explicit encoding an error; that warning does not see standard input and output, which the Shift JIS run covers. It tests invalid fixtures and checks a temporary distribution folder named `notion-ai-relay`, independently of the checkout's name. The staged files are every file git tracks, plus new files that git's ignore rules do not exclude, without `metadata.json`, because `npx skills add` installs the whole repository except `metadata.json`. Run it from a git checkout. To check an installed copy instead, run `python3 scripts/check_structure.py --skill-dir /path/to/notion-ai-relay` from the development environment; a relative path such as `.` also works. When that folder is the top of a git checkout, only the files that would be staged are checked, so a `.venv` inside it is ignored. Every failure names the file it came from.

Checks cover YAML syntax (including duplicate keys), required files, a `cases.json` in every `evals/` folder whose cases each have a unique `id` and a non-empty expected outcome, [Agent Skills frontmatter constraints](https://agentskills.io/specification), folder/name agreement, local links in Markdown (including HTML `a href` and `img src`) and heading anchors, and the display fields and Skill reference in [Codex metadata](https://github.com/openai/skills/blob/main/skills/.system/skill-creator/references/openai_yaml.md). The Codex display fields are optional in the general format but required by this repository's distribution check. Codex string values must be quoted and keys unquoted. The usefulness of descriptions still needs review. External URLs are not fetched. A link to a folder only needs the folder to exist. Code examples and bare paths are not checked as references.

**A structural PASS is not a model-execution or Notion-compatibility PASS.** It does not prove that a client loads the Skill, that an assistant follows the instructions, or that MCP access is available. GitHub-hosted CI execution must be confirmed separately from a local run.
