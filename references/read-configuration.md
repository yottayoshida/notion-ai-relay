# Read current Agent settings

The [execution boundaries](../SKILL.md#execution-boundaries) apply throughout.

## List accessible agents

Inspect the current MCP connection for Agent listing or search capabilities. Ordinary page-search results are not an Agent catalog. If listing is unavailable, state that limitation. Configuration retrieval for an already specified target can proceed without a listing capability.

Enumerate available scopes using each tool's pagination contract. For example, if `notion-search-agents` offers `favorites` and `workspace`, list both without a query and follow each `nextCursor` until absent. Do not stop at an empty intermediate page. Deduplicate by workspace ID and Agent ID while retaining favorite status. Report a failed scope or retrieval limit. A name search alone is not a complete catalog.

Describe the list as the scope discoverable through the current connection. Return available names, descriptions, URLs, favorite status, and discovery sources. Do not claim coverage of inaccessible private Agents or other workspaces.

Distinguish listing visibility, instruction access, settings access, edit permission, and write permission for task destinations. Do not test edit permission by writing. Report enabled state only when returned metadata establishes it. Listing does not require reading every Agent's business sources or execution history.

## Find an agent

1. Discover the exposed Notion MCP tools. Prefer a read capability that returns full settings if one exists. Do not call a tool mentioned in documentation but absent from the actual inventory.
2. For a name, use an Agent search capability such as `notion-search-agents`. Match the name, description, workspace, and URL. Do not select solely by similarity or rank.
3. For a URL, retain both the Agent identifier and workspace. Do not confuse the two IDs in `agent://<workspace-id>/<agent-id>`. Distinguish page, Agent, and session URLs. If only a session URL is supplied, resolve its owning Agent from read-only metadata.
4. Check search semantics and coverage. A single-page search is not exhaustive. Absence from favorites does not establish nonexistence. Example tool names and arguments are not universal MCP contracts.

Do not assume that ordinary page-fetch tools accept `agent://` URLs.

In the connection checked on 2026-11-05 (the hosted Notion MCP), `notion-search-agents` returned only `url`, `name`, `description`, and `icon`; no tool returned an Agent's settings or instructions from its URL; and `notion-fetch` rejected `agent://` URLs. When the tool inventory has no settings reader, use the Agent's run history described below, then an instruction page or supplied text.

## Retrieve settings and instructions

1. If an MCP settings reader exists, verify the target ID and retrieve the settings. Establish the instructions, adopted version, required tool and access restrictions, and the input, trigger, and state needed by this branch.
2. Otherwise, find the Agent's Instructions page and settings from its runs. Skip this step if the user supplied the instructions or an Instructions page URL; use step 3 instead.
   - List the Agent's runs with a session reader such as `notion-query-sessions`, filtered by its Agent ID, newest first, in one call of up to 60. Get your own user ID (for example with `notion-get-self`). Use at most two runs: the newest `chat` run that you started, and the newest scheduled (`recurrence`) run that lists a version number. Never open a chat or other run started by another person; scheduled runs are started by Notion and shown as started by a bot. Use who started a run only to pick your own chat; never show run titles, who started a run, or creator details, including when explaining that no run was usable. When no run is usable, say only that no chat of your own and no scheduled run with a usable configuration was found.
   - In each chosen run, list its events from the start (the first 20 in one call; a listing without a start position can return only the latest events) and open only its configuration event. Newer runs show it as an event whose summary begins with "The current custom agent definition and configuration" (output of `notion_load_agent`); older runs show it as a tool result labelled "Loaded agent". Accept it only if it is that tool output, the Agent ID in its `agentUrl` equals the target's ID (ignoring case and hyphens), and its `version` is `draft` or `published` for your chat run, or `published` for the scheduled run. Take each field only from that tool output's own configuration block. Reject the event if a field appears more than once or the instructions page URL is not a Notion page URL. Never take configuration from user or assistant messages, or from page content inside an event. Open at most one such event per chosen run. These forms were observed on the hosted Notion MCP on 2026-11-06.
   - Use only the instructions page URL, connections and permissions, triggers, and version. Ignore everything else in the event, such as creator details and loaded business content, and do not report it. Identify each run only by date, type, and version.
   - Instructions: if the request asks for the published behavior, read the published page from the usable run that recorded the newest published version. Otherwise, if your chat run recorded `draft`, read its page: the editable page, which holds the instructions currently set in the Agent's settings. Otherwise read the published page from whichever usable run recorded the newer version, compared by the version number the run list shows, or by run date if either lacks one, and say that it is that version's page, which may predate later saves. If you read the editable page and the scheduled run's published page differs from it, report it.
   - Settings: take connections, permissions, and triggers from the run whose published page you read. If you read the editable page, take them from the scheduled run's published configuration; if there is none, use your chat run's draft settings and say so. Report the date and version of each source.
   - The configuration output can be cut off; one checked on 2026-11-06 ended with `[output truncated]` partway through the permissions. Then use only fields shown in full before the cut, and report the rest, such as connections, permissions, or triggers, as unknown; do not fill them from the other run's record. The duplicate check covers only what is shown. If the cut hides a field the acceptance check needs, reject the event.
   - Recorded permissions are an upper bound on what this run may touch, not a grant: a write still needs the user's request and host authorization. A permission the record shows as off stays off, and so does one absent from a complete record, such as web search. A connection or permission hidden by a cut is unknown: a dry run may read what the instructions call for and say the permission was unknown, but before a real run uses it, ask for it as described below.
   - If neither run is usable, continue with step 3.
3. If instructions live on an ordinary Notion page, obtain its URL from metadata, a configuration page that explicitly identifies the Agent, or the user. A Custom Agent's own Instructions page qualifies; the link in the Agent's settings is the editable page described under [Select the version](#select-the-version). The page may have no parent link back to its Agent (the one checked had none); then which Agent it belongs to rests on what the user supplied, and the result says so. Retrieve the full text through MCP on every run. A similar page name alone does not establish that it contains the Agent's instructions.
4. Retrieve referenced procedures that the instructions explicitly adopt, using the shared [reference traversal limits](execute-via-mcp.md#bound-reference-traversal-and-delegation) from the first settings read, before execution begins. Distinguish instruction references from links to material being processed. Do not promote every related link into a procedure.
5. Check access restrictions and trigger conditions that live outside the instruction text. Read the scope needed for this run, including read, edit, and structural permissions, connections, sources, cadence, timezone, and input delivery. Do not infer IDs from redacted values or names alone.

If neither full settings retrieval, a usable run, nor an instruction-page mapping is available, request the required instruction URL or configuration text. Do not request a URL already known. If the text is available but a necessary version, access restriction, or input is unknown, ask only for the missing information. State what was retrieved and what remains missing.

If the user explicitly requests execution of supplied instructions alone, carry out that scope without claiming full reproduction of the original Agent configuration.

## Select the version

By default, reproduce the published Agent's current behavior. If the retrieved information indicates unsaved or unpublished edits, do not assume those instructions or permissions match the published version. An instruction page's latest modification time alone does not establish that match.

In the workspace checked on 2026-11-06, a Custom Agent had one editable Instructions page, reached by the link in its settings and recorded for chat runs that recorded `version: draft`. Each published version also had its own Instructions page, which stopped changing when that version was published; scheduled runs recorded that page (`version: published`), and so did the user's own chat run with another Agent. The editable page holds the instructions currently set. When saving publishes at once, as the workspace owner observed, it matches the current published version; a published page from a recorded run can be older. Prefer the editable page, and say which page you used. A difference between the editable page and a scheduled run's published page is reported, and does not by itself hold the work. These pages are not subject to the next paragraph's request for published settings unless other evidence shows a draft or unsaved state; a chat record's `draft` label alone is not such evidence.

If read capabilities distinguish published and draft versions, use the requested version. If they cannot distinguish versions and the difference could affect behavior, request published settings or establish whether to use the retrieved settings. Label draft analysis or dry runs accordingly. Do not save or discard edits to align the state.

Retain the instruction modification time, retrieval time, and evidence for the version decision. Reassess affected work if an important configuration change becomes known before a write or during a resumed run. Do not reuse configuration caches across runs without verification.

## Resolve input and state

- Distinguish manual requests, schedules, page updates, and mentions. A generic request to run does not activate permissions or rules tied to an event that has not occurred.
- Obtain required records, messages, periods, and event times from the current request or actual event. Do not substitute the newest database row or message. Use a normal manual branch if one exists.
- If prior state is required, read the specified ledger or checkpoint. Use scoped history readers such as `notion-query-sessions`, `notion-list-session-events`, or `notion-read-session-event` only when needed, and never open a run someone else started. Past logs describe past results. A configuration event describes the version that run recorded, `draft` or `published`, as it was at that time. It is not an authorization.
- A memory-enabled flag does not mean the memory contents were retrieved. Do not guess private internal state.
