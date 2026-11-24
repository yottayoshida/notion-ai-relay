# Reading Custom Agent instructions and settings

Notion AI Relay needs a Custom Agent's instructions before it can carry out the Agent's task. This page compares the ways to get them and records test runs. It is for users comparing routes and for maintainers; the Skill does not load it.

Scope of the checks: one Notion workspace, three Custom Agents, read by a user who can edit the first two (edit access to the third was not checked), using Claude Code with the hosted Notion MCP. These 2026-11-06 records were not rerun on 2026-11-15. Other plans, roles, and clients may differ.

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
| Hosted Notion MCP: run history (`notion-query-sessions`, `notion-list-session-events`, `notion-read-session-event`) | Read access to the Agent's runs, and a chat you had with it or a scheduled run | From the configuration event Notion recorded for the run: the Instructions page URL (the editable page for a run that recorded `draft`, that version's page for one that recorded `published`), connections and permissions, triggers, and version | For a run that recorded `published`: edits saved after that version. Settings past the point where Notion cut the output short | Tool calls on 6 runs of 3 Agents, 2026-11-06 |
| Hosted Notion MCP: `notion-fetch` on the Agent's Instructions page | Read access to the page, and its URL from a recorded run or from the Agent's settings | Full instruction text of the page tested, and its last edited time | Triggers, connections, status, version, and a link from the page back to its Agent (the page had no parent) | Tool calls, 2026-11-06 |
| Hosted Notion MCP: Notion Skills | A Skill enabled for external MCP clients, or the Skill's page URL | `id`, name, and description from `notion-get-enabled-skills`; page text from `notion-fetch` with that `id` | Whether an Agent's instructions can hand off to a Skill (not tested) | Tool calls, 2026-11-05 |
| Notion Agent API: `POST /v1/agents/query` (REST) | A personal access token (on Business and Enterprise plans, off until a workspace owner allows it) or an internal connection with **View sessions and interact with agents** and the Agent shared with it | `instructions` (inline, with `verbose`), `instructions_page_id`, `triggers`, `connections` (including MCP tool settings), `status`, `agent_version` | — | [API reference](https://developers.notion.com/reference/notion-agent-apis/query-agents) read 2026-11-06; not run |
| Notion Agent API: `GET /v1/agents/{agent_id}` (REST) | A token that can read the Agent; `has_unpublished_changes` needs edit access | `instructions_page_id`, `connections`, `triggers`, `version` (`number`, `published_at`), `has_unpublished_changes`, `pause_reason`, `status`, and `instructions` with `verbose` | — | [API reference](https://developers.notion.com/reference/notion-agent-apis/retrieve-agent) read 2026-11-24; not run |
| Official open-source MCP server (`makenotion/notion-mcp-server`) | An integration token | — | Agents: none of the 17 paths in its OpenAPI spec is an agent path | Spec read 2026-11-06 |

Notes on the rows:

- **One editable page, one frozen page per published version.** For the first two Agents, the link in an Agent's settings, and the configuration recorded for the user's chat runs (`version: draft`), pointed to the same editable page, which kept changing. For the third Agent, the user's own chat run recorded `version: published` and that version's page; why it differed was not determined. Scheduled runs (`version: published`) pointed to a different page for each version, and each of those stopped changing when its version was published. The editable page held an edit that the latest recorded published page did not. Whether that edit was later published was not visible without a newer run.
- **What a run records.** In each run checked, one event held the Agent's configuration. In newer runs it was the output of Notion's internal `notion_load_agent`, with a summary beginning "The current custom agent definition and configuration": the 10th event in scheduled runs and the 11th in a chat run. In an older chat run it was a tool result labelled "Loaded agent", the 9th event. Match on content, not position. In the third Agent's chat run, the configuration output ended with `[output truncated]` partway through the permissions; later connections and the triggers were not in the record. The same event also carries the creator's details and loaded business content. The run list shows run titles, including other people's chats. On 2026-11-24 it also returned each run's `trigger_type` (`chat`, `recurrence` and `slack.app.mention` were seen), `type_labels`, `agent_version` with `number` and `published_at`, and `chat_user_emails`, the participants' addresses; a run a bot started for a Slack mention showed the people in that thread. From the configuration event the Skill uses only the configuration fields, and it reports runs by date, type, and version.
- **The Agent API can read one Agent.** `GET /v1/agents/{agent_id}` returns the published version's number and time and whether the draft has unpublished edits, which would settle what [Select the version](../references/read-configuration.md#select-the-version) reasons around. It needs a token like the query route, and `has_unpublished_changes` shows only with edit access. On 2026-11-24 the hosted Notion MCP had no settings reader; the Skill uses one only when a connection offers it.
- **The Agent API needs a token with more than read access.** The capability that lets a connection read Agents also lets it start sessions. The [Notion Agents SDK README](https://github.com/makenotion/notion-agents-sdk-js) says "public integration access [is] not supported", so an OAuth integration such as the hosted Notion MCP is not a documented way in.
- **Tool names differ by layer.** On 2026-11-05 the hosted Notion MCP's tool list named the Agent search `notion-search-agents`, while its access map from `notion-get-tool-access` called it `search_agents`; see [runtime requirements](../SKILL.md#runtime-requirements).
- **Enabled-Skill list.** Notion's [tools reference](https://developers.notion.com/guides/mcp/tools-skills-agents-reference), read 2026-11-24, says "The list holds at most 30 Skills and has no cursor, so a user with more enabled Skills doesn't see all of them"; the tool's own description gives neither the maximum nor the missing cursor. The same section says long names and descriptions are shortened. [Notion's help](https://www.notion.com/help/skills-for-notion-agent), read the same day, gives 50 as the number of Skills a connected agent loads per session, which is a different limit. The Skill carries the documented 30 with its date and reports a list of at least that length as possibly incomplete; a lower maximum in future would go unnoticed until the date is checked.
- **Rate limits.** Notion's [rate limits](https://developers.notion.com/guides/mcp/rate-limits) page, read 2026-11-24, says a limited call returns `rate_limited` with `retry_after_seconds` when known, and that the server retries once itself only when the wait is 2 seconds or less; it advises fewer parallel operations or trying again later, and does not separate reads from writes. A client therefore mostly sees waits longer than 2 seconds, and an immediate retry would be refused again. The Skill repeats such a read once after the wait only when the client has a way to wait, and otherwise holds what depends on it; a retry rule in the procedure comes first. It does not repeat writes this way: whether a refused write took any effect is not documented, so the existing rules apply: an operation that failed is not repeated for the same cause, and a creation or message whose outcome is unknown is not resent.
- **Tracking argument.** On 2026-11-24 every hosted Notion MCP tool took an optional `skill` argument, described as "For tracking only: the name of the agent skill you are following for this task", and an optional `instructions_version` ("Omit if unknown"). Notion's [tools reference](https://developers.notion.com/guides/mcp/tools-skills-agents-reference), read the same day, describes neither. Passing `skill` would tell Notion which Skill made each call, so the Skill leaves it out (owner's decision, 2026-11-24, to be revisited if Notion documents the argument).
- **Browser routes were not pursued.** The Agent API documents the fields, browser automation is client-specific, and private endpoints can change without notice.

## What the run-history route assumes

Running an Agent by name rests on the following; the observations behind them are dated on this page.

1. **The configuration event is internal output.** Notion's documentation, as read on 2026-11-24, describes neither form the Skill matches (see What a run records above). If Notion changes the form, a request by name finds no usable run and asks for the Instructions page URL, without saying that the form changed. The user can give that URL or paste the instructions. A maintainer should read the events of a fresh run of their own and update the match in [configuration retrieval](../references/read-configuration.md#retrieve-settings-and-instructions).
2. **The event comes early in a run.** The Skill lists a run's events from the start and reads on once; if the event moves further back than that, by-name requests fail as in 1.
3. **The run list's fields pick the runs.** The Skill chooses runs by their trigger type (`chat` or `recurrence`), who started them, and the version number the list shows, as seen on 2026-11-24. If these fields change, no run may be usable, as in 1; if only scheduled runs stop being recognised, settings come from your chat's record.
4. **Reading the editable page needs your chat among the latest 60 runs.** A run a bot started for a mention or a page event is someone else's (see the run-list fields above). An Agent that runs mostly on such events can push your own chats out of the 60 runs read, and the Skill cannot say why without mentioning other people's runs. Chat with the Agent shortly before, which is itself a Notion run of the Agent, shown in its Activity and run with its own permissions, or give the Instructions page URL.
5. **Saving publishes at once.** The Skill prefers the editable Instructions page because the owner observed that saving it publishes at once (see Not tested). Where an Agent keeps unpublished edits, the editable page can differ from what Notion runs; ask for the published behavior, and the Skill reads the newest published page recorded instead.
6. **The record ages once Relay replaces the Agent.** A run is recorded only when Notion runs the Agent. If you stop its schedule and carry out its task through Relay instead, the recorded connections, permissions and triggers stay at the last Notion run, and so do the instructions unless a chat of yours recorded the editable page. A new chat with the Agent in Notion refreshes your chat's record, but settings still come from the latest scheduled run while one is among the latest 60 runs, unless your chat recorded a newer published version. Giving the Instructions page URL skips the run history, and with it the recorded settings. The Skill reports the date of each record; expect that date to fall behind.
7. **A relayed run is not one of the Agent's runs.** It takes place in your assistant, not in Notion. On 2026-11-24 the run list read through MCP, taken here to match the Activity that only users with full access see, showed no run on 2026-11-06 for an Agent that had been dry-run through Relay that day. [Notion's help](https://www.notion.com/help/custom-agents), read 2026-11-24, describes the Activity as a log of the Agent's runs and Memories as what the Agent learns from its own chats; it says nothing about work done outside Notion, so that a relayed run neither uses nor adds to the Agent's Memories is inferred, not observed. The [README](../README.md#requirements-and-limits) states both limits.

## Recommendation

Give the Agent's name, as described under Use in the [README](../README.md#use). The Skill reads the editable Instructions page, which holds the instructions currently set, when a chat you had with the Agent recorded it, and takes settings from its latest scheduled run, with no token. Otherwise it uses the newest published page recorded for your chat or a scheduled run, which may predate later saves. If no run is usable, give the Instructions page URL or the text. Settings cut from a record are reported as unknown. Other people's runs are never opened. Whichever route supplied the instructions, the Skill waits for a go-ahead before operations the user did not name, as the [execution boundaries](../SKILL.md#execution-boundaries) set out; with instructions from a recorded run it also gives the run date, because the Agent's permissions may have changed since that run.

## Not tested

- Whether a user who can run an Agent but cannot edit it can read the Agent's runs or Instructions page.
- Whether every Custom Agent has an Instructions page. The Agent API also has an inline `instructions` field.
- When an edit on the editable page becomes a new published version. The owner observed that saving publishes at once; the next scheduled run's version number and page will confirm it.
- What makes a chat run record `draft` or `published`.
- When Notion cuts the configuration output short.
- Runs started by mentions or page events, and whether their configuration event has the same form.
- How Skills attached to an Agent under Tools and access, and an Agent's Memories, appear in the recorded configuration, and whether their contents can be read through MCP. On 2026-11-24 the configuration recorded in a chat of the user's own with one Agent was cut off in the connections, before any such field could appear; the run list's `tool_types` field for some of the user's chats included `connections.skills.loadSkill`. The Skill reports attached Skills and the Memories setting only when a record shows them, under names it does not know in advance; a complete record that shows neither is not taken to mean the Agent has none.
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

### 2026-11-06: by name only, a third Agent, interactive session

The Skill as of the previous section was installed in the user's client. The user asked for a dry run by the Agent's name in an interactive Claude Code session.

- The Agent had no scheduled runs among its runs; all were the user's own chats.
- The newest chat run's configuration event recorded `version: published` and that version's Instructions page. The rule then in force accepted only `draft` from a chat run, so the Skill rejected the record and asked for an Instructions page URL. The user chose to continue with the recorded page.
- The configuration output was cut off partway through the permissions. Connections after that point and the triggers were unknown.
- Result: a dry-run report with nothing written. It said a real run would stop before writing because some source pages could not be read.
- Changes made after this run: a chat run may record either version, the newer published page is used when there is no draft, and settings missing from a cut-off record are reported as unknown.
