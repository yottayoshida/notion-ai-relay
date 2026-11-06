# Reading Custom Agent instructions and settings

Notion AI Relay needs a Custom Agent's instructions before it can carry out the Agent's task. This page compares the ways to get them and records test runs. It is for maintainers; the Skill does not load it.

Scope of the checks: one Notion workspace, two Custom Agents, read by a user who can edit them, using Claude Code with the hosted Notion MCP. Other plans, roles, and clients may differ.

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
| Hosted Notion MCP: run history (`notion-query-sessions`, `notion-list-session-events`, `notion-read-session-event`) | Read access to the Agent's runs, and a chat you had with it or a scheduled run | From the configuration event Notion recorded for the run: the Instructions page URL (editable page for a chat, published page for a scheduled run), connections and permissions, triggers, and version | For a scheduled run only: edits saved after that run | Tool calls on 5 runs of 2 Agents, 2026-11-06 |
| Hosted Notion MCP: `notion-fetch` on the Agent's Instructions page | Read access to the page, and its URL from a recorded run or from the Agent's settings | Full instruction text of the page tested, and its last edited time | Triggers, connections, status, version, and a link from the page back to its Agent (the page had no parent) | Tool calls, 2026-11-06 |
| Hosted Notion MCP: Notion Skills | A Skill enabled for external MCP clients, or the Skill's page URL | `id`, name, and description from `notion-get-enabled-skills`; page text from `notion-fetch` with that `id` | Whether an Agent's instructions can hand off to a Skill (not tested) | Tool calls, 2026-11-05 |
| Notion Agent API: `POST /v1/agents/query` (REST) | A personal access token (on Business and Enterprise plans, off until a workspace owner allows it) or an internal connection with **View sessions and interact with agents** and the Agent shared with it | `instructions` (inline, with `verbose`), `instructions_page_id`, `triggers`, `connections` (including MCP tool settings), `status`, `agent_version` | — | [API reference](https://developers.notion.com/reference/notion-agent-apis/query-agents) read 2026-11-06; not run |
| Official open-source MCP server (`makenotion/notion-mcp-server`) | An integration token | — | Agents: none of the 17 paths in its OpenAPI spec is an agent path | Spec read 2026-11-06 |

Notes on the rows:

- **One editable page, one frozen page per published version.** The link in an Agent's settings, and the configuration recorded for a chat run (`version: draft`), pointed to the same editable page, which kept changing. Scheduled runs (`version: published`) pointed to a different page for each version, and each of those stopped changing when its version was published. The editable page held an edit that the latest recorded published page did not. Whether that edit was later published was not visible without a newer run.
- **What a run records.** In each run checked, one event held the Agent's configuration. In newer runs it was the output of Notion's internal `notion_load_agent`, with a summary beginning "The current custom agent definition and configuration": the 10th event in scheduled runs and the 11th in a chat run. In an older chat run it was a tool result labelled "Loaded agent", the 9th event. Match on content, not position. The same event also carries the creator's details and loaded business content. The run list shows run titles, including other people's chats. The Skill uses only the configuration fields and reports runs by date, type, and version.
- **The Agent API needs a token with more than read access.** The capability that lets a connection read Agents also lets it start sessions. The [Notion Agents SDK README](https://github.com/makenotion/notion-agents-sdk-js) says "public integration access [is] not supported", so an OAuth integration such as the hosted Notion MCP is not a documented way in.
- **Browser routes were not pursued.** The Agent API documents the fields, browser automation is client-specific, and private endpoints can change without notice.

## Recommendation

Give the Agent's name, as described under Use in the [README](../README.md#use). The Skill reads the editable Instructions page, which holds the instructions currently set, found through a chat you had with the Agent, and takes settings from its latest scheduled run, with no token. Without your own chat it falls back to the published page of the latest scheduled run, which may predate later saves. Otherwise give the Instructions page URL or the text. Other people's runs are never opened. When the instructions or settings come from a recorded run, the Skill lists every write destination the user did not name in the request, with the run date, and waits for the user's go-ahead before the first write, because the Agent's permissions may have changed since that run.

## Not tested

- Whether a user who can run an Agent but cannot edit it can read the Agent's runs or Instructions page.
- Whether every Custom Agent has an Instructions page. The Agent API also has an inline `instructions` field.
- When an edit on the editable page becomes a new published version. The owner observed that saving publishes at once; the next scheduled run's version number and page will confirm it.
- Runs started by mentions or page events, and whether their configuration event has the same form.
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

### 2026-11-06: by name only, through run history

Same client and isolation as above, with the three session readers added to `--allowedTools`.

- Supplied by hand: the Agent's name and a limit of 3 candidates. No URL and no instructions.
- Calls, in order:
  - `notion-search-agents`
  - `notion-get-self`
  - `notion-query-sessions`, once, filtered by the Agent's ID, up to 60 runs
  - `notion-list-session-events`, once each, on the user's own chat run and the latest scheduled run (the first 20 events)
  - `notion-read-session-event`, once each, on those two runs' configuration events
  - `notion-fetch` on the editable Instructions page (from the chat run) and on the published page (from the scheduled run)
  - then the Agent's sources
- Not called: a fetch of the `agent://` URL, any session-control tool, any write tool. No run started by someone else was opened. One read tool outside the test's allowed list was refused (a Slack user lookup).
- Result: a dry-run report. It said the instructions came from the editable page and the settings from the scheduled run's published version, with dates. It reported that the two pages differed in one rule. No run titles, creator details, or email addresses appeared in it.
- Control: the same prompt with the previous version of these instructions called no session reader. After 6 searches it stopped without starting the dry run, because it could not get the instructions.
