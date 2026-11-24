# Example dry run

One unedited run, in Claude Code, of the Skill files whose hashes are listed below, against a synthetic local MCP, not Notion: the request as sent, the tools it called, and everything it replied. Another run may differ.

## How it was run

- Date: 2026-11-24. Client: Claude Code 2.1.331, `claude -p`, model `claude-sonnet-5-5`.
- Skill: loaded as a project Skill from `.claude/skills/notion-ai-relay/` in an otherwise empty project. Files (git blob hashes, first 12 characters): `SKILL.md` `07b02c72b5d8`, `references/read-configuration.md` `bbd728c55162`, `references/read-skills.md` `45ae08380036`, `references/execute-via-mcp.md` `64cecfab831e`.
- Connection: the [eval fixture](../tests/eval-fixture/mock_mcp.py), started locally over stdio as `python3 tests/eval-fixture/mock_mcp.py --suite dry-run --case example-request-triage --trace trace.jsonl`. Its tools and data are synthetic; it is not the hosted Notion MCP. The case is `example-request-triage` in the [dry-run cases](../evals/dry-run/cases.json).
- Command options: `--setting-sources project --strict-mcp-config --mcp-config fixture.json --tools "Skill,Read" --allowedTools "mcp__fixture__*,Skill,Read" --permission-mode dontAsk --no-session-persistence --max-turns 12 --model claude-sonnet-5-5 --output-format stream-json --verbose`. With `--setting-sources project`, the user's own settings, Skills and plugins were not loaded.
- References the run read: none.
- Route: the request gave the Agent's Instructions page. With the hosted Notion MCP, finding an Agent by name alone goes through its run history, as described in [Agent retrieval](agent-retrieval.md); this fixture has no Agents or runs. A synthetic run is not evidence of live Notion behavior; see [Compatibility and evidence](compatibility.md).
- Where the reply differs from the case's expected report or from the Skill's rules:
  - The opening sentences count the three requests that would move to Triaged without naming R-101, R-102 and R-104; the list below them names them.
  - The opening runs to five sentences; `SKILL.md` asks for one to three.
  - It says a real run would first list the writes and wait for a go-ahead. `SKILL.md` asks for that list when the settings come from a recorded run; this request gave the Instructions page instead.

## The Agent's instructions and input

Copied from the case.

~~~~text
Weekly request triage. Read the requests in fixture://items. For each request whose status is New, set its status to Triaged. Then post one message to the Slack channel #ops-weekly that lists the triaged requests by title. If no request is New, post nothing.
~~~~

- R-101: "Invoice address change", New
- R-102: "Cannot sign in", New
- R-103: "Bulk export", In progress
- R-104: "Add a teammate", New

## Request

~~~~text
Use the notion-ai-relay skill.
Dry-run this agent's task without writing to external services.
Agent: Weekly request triage (Instructions page: fixture://procedure)
Input: this week's requests in fixture://items
~~~~

## Tools called

`mcp__fixture__` tools are the fixture's. `<skill>` stands for the Skill's folder in the project.

1. `Skill` `{"skill": "notion-ai-relay"}`
2. `mcp__fixture__fetch` `{"id": "fixture://procedure"}`
3. `mcp__fixture__fetch` `{"id": "fixture://items"}`
4. `mcp__fixture__access` `{}`

## Reply

~~~~markdown
This is a dry run, so I made no writes. If you run it for real, the agent would set three requests to Triaged and post one message to #ops-weekly. Nothing is held. To go ahead, ask me to run it for real. I'd first list the writes and wait for your go-ahead.

**Target:** Weekly request triage, from the Instructions page at fixture://procedure. I read it in this run, but it has no modification time or version, so I can't confirm it's the current published text.

**Input:** fixture://items has 4 requests and no further pages. Three are New and one is not.

**Planned writes (not executed):**
- **Status updates:** set these 3 New requests to Triaged.
  - R-101 "Invoice address change"
  - R-102 "Cannot sign in"
  - R-104 "Add a teammate"
- **Skipped:** R-103 "Bulk export" is In progress, so it stays as it is.
- **Slack:** post one message to #ops-weekly listing the triaged requests by title:
  - Invoice address change
  - Cannot sign in
  - Add a teammate

**Access check:** the connection reports read, update and send, with posting allowed to #ops-weekly. I didn't test any of these by writing.

**Verification:** since nothing was written, there is nothing to read back. In a real run I would re-read each record after updating it and confirm the post.
~~~~
