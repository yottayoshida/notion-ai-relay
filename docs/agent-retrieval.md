# Reading Custom Agent instructions and settings

Notion AI Relay needs a Custom Agent's instructions before it can carry out the Agent's task. This page compares the ways to get them and records test runs. It is for maintainers; the Skill does not load it.

Scope of the checks: one Notion workspace, one Custom Agent, read by a user who can edit that Agent, using Claude Code with the hosted Notion MCP. Other plans, roles, and clients may differ.

## Four separate questions

- **Discovery**: which Agents exist and what are their URLs.
- **Instruction retrieval**: the text the Agent follows.
- **Full configuration**: triggers, connections and their tool permissions, status, and version.
- **Authorization to execute**: comes from the current user's request and the host's permissions, as set out in the [execution boundaries](../SKILL.md#execution-boundaries).

## Routes

| Route | Needs | Gets | Does not get | Checked |
|---|---|---|---|---|
| Hosted Notion MCP: `notion-search-agents` | Read access to the Agent | `url` (`agent://…`), `name`, `description`, `icon` | Instructions, triggers, connections, status, version | Tool call, 2026-11-05 |
| Hosted Notion MCP: `notion-fetch` on an `agent://` URL | — | Nothing: `400`, "URL type agent not currently supported for fetch tool." | — | Tool call, 2026-11-05 |
| Hosted Notion MCP: `notion-fetch` on the Agent's Instructions page | Read access to the page, and its link copied from the Agent's settings | Full instruction text of the page tested, and its last edited time | Triggers, connections, status, version, and a link from the page back to its Agent (the page had no parent) | Tool call, 2026-11-06 |
| Hosted Notion MCP: Notion Skills | A Skill enabled for external MCP clients, or the Skill's page URL | `id`, name, and description from `notion-get-enabled-skills`; page text from `notion-fetch` with that `id` | Whether an Agent's instructions can hand off to a Skill (not tested) | Tool calls, 2026-11-05 |
| Notion Agent API: `POST /v1/agents/query` (REST) | A personal access token (on Business and Enterprise plans, off until a workspace owner allows it) or an internal connection with **View sessions and interact with agents** and the Agent shared with it | `instructions` (inline, with `verbose`), `instructions_page_id`, `triggers`, `connections` (including MCP tool settings), `status`, `agent_version` | — | [API reference](https://developers.notion.com/reference/notion-agent-apis/query-agents) read 2026-11-06; not run |
| Official open-source MCP server (`makenotion/notion-mcp-server`) | An integration token | — | Agents: none of the 17 paths in its OpenAPI spec is an agent path | Spec read 2026-11-06 |

Notes on the rows:

- **Saving publishes.** In the workspace checked on 2026-11-06, saving a Custom Agent published it at once, with no separate draft. So the Instructions page showed what the Agent runs.
- **The Agent API needs a token with more than read access.** The capability that lets a connection read Agents also lets it start sessions. The [Notion Agents SDK README](https://github.com/makenotion/notion-agents-sdk-js) says "public integration access [is] not supported", so an OAuth integration such as the hosted Notion MCP is not a documented way in.
- **Browser routes were not pursued.** The Agent API documents the fields, browser automation is client-specific, and private endpoints can change without notice.

## Recommendation

Give the Instructions page URL, as described under Use in the [README](../README.md#use); it needs no token. Triggers, connections, and status are not available over the hosted Notion MCP, so the Skill asks for a setting only when the current task needs it.

## Not tested

- Whether a user who can run an Agent but cannot edit it can read the Agent's Instructions page.
- Whether every Custom Agent has an Instructions page. The Agent API also has an inline `instructions` field.
- Whether editing the Instructions page directly, rather than through the Agent's settings, takes effect at once.
- Whether `notion-fetch` truncates a long Instructions page.
- Agent instructions that hand off to a Notion Skill.
- Page and block reads through the Notion REST API.

## Recorded runs

### 2026-11-06: Claude Code 2.1.318, claude-opus-5-5

Setup:

- The Skill was copied into `.claude/skills/notion-ai-relay/` of an empty project.
- The client reached Notion and Slack through the connectors of a claude.ai account.
- Each run used `claude -p` with `--setting-sources project` and `--permission-mode dontAsk`.
- `--allowedTools` listed only read tools. `--disallowedTools` listed every Notion write and session tool and every Slack write tool, so neither run could write even if asked to.

**Custom Agent, dry run**

- Supplied by hand: the Agent URL, its Instructions page URL, and a limit of 5 candidates.
- Calls, in order:
  - `notion-get-tool-access` once
  - `notion-fetch` on the Instructions page
  - `notion-fetch` on the 3 pages the instructions name
  - `slack_search_channels`, `slack_read_channel`, and `notion-search` once each
  - `slack_read_thread` 5 times (1 returned `thread_not_found`)
  - `notion-query-data-sources` once
- Not called: a fetch of the `agent://` URL, any session tool, any write tool. Permission denials: 0.
- Result: a dry-run report. It covered access per source, 5 candidates, the unchecked range, and a resume point, and it named the Instructions page's last edited time as the version used. 20 turns, 74 s.

**Notion Skill**

- Supplied by hand: the Skill's name and a short made-up OKR as material.
- Calls: `notion-get-enabled-skills` once, then `notion-fetch` once with the listed `id`. Permission denials: 0.
- Result: a review as text, with the instruction page's last edited time. Nothing was written. 7 turns, 52 s.

**Install folder name**

With the same files, Claude Code listed the Skill as `notion-ai-relay-main` when the folder had that name. It listed `notion-ai-relay` only after the folder was renamed.
