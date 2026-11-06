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

In the connection checked on 2026-11-05 (the hosted Notion MCP), `notion-search-agents` returned only `url`, `name`, `description`, and `icon`; no tool returned an Agent's settings or instructions; and `notion-fetch` rejected `agent://` URLs. When the tool inventory has no settings reader, go to the instruction page or supplied text described below.

## Retrieve settings and instructions

1. If an MCP settings reader exists, verify the target ID and retrieve the settings. Establish the instructions, adopted version, required tool and access restrictions, and the input, trigger, and state needed by this branch.
2. If instructions live on an ordinary Notion page, obtain its URL from metadata, a configuration page that explicitly identifies the Agent, or the user. Retrieve the full text through MCP. A similar page name alone does not establish that it contains the Agent's instructions.
3. Retrieve referenced procedures that the instructions explicitly adopt. Distinguish instruction references from links to material being processed. Do not promote every related link into a procedure.
4. Check access restrictions and trigger conditions that live outside the instruction text. Read the scope needed for this run, including read, edit, and structural permissions, connections, sources, cadence, timezone, and input delivery. Do not infer IDs from redacted values or names alone.

If neither full settings retrieval nor an instruction-page mapping is available, request the required instruction URL or configuration text. Do not request a URL already known. If the text is available but a necessary version, access restriction, or input is unknown, ask only for the missing information. State what was retrieved and what remains missing.

If the user explicitly requests execution of supplied instructions alone, carry out that scope without claiming full reproduction of the original Agent configuration.

## Select the version

By default, reproduce the published Agent's current behavior. If the retrieved information indicates unsaved or unpublished edits, do not assume those instructions or permissions match the published version. An instruction page's latest modification time alone does not establish that match.

If read capabilities distinguish published and draft versions, use the requested version. If they cannot distinguish versions and the difference could affect behavior, request published settings or establish whether to use the retrieved settings. Label draft analysis or dry runs accordingly. Do not save or discard edits to align the state.

Retain the instruction modification time, retrieval time, and evidence for the version decision. Reassess affected work if an important configuration change becomes known before a write or during a resumed run. Do not reuse configuration caches across runs without verification.

## Resolve input and state

- Distinguish manual requests, schedules, page updates, and mentions. A generic request to run does not activate permissions or rules tied to an event that has not occurred.
- Obtain required records, messages, periods, and event times from the current request or actual event. Do not substitute the newest database row or message. Use a normal manual branch if one exists.
- If prior state is required, read the specified ledger or checkpoint. Use scoped history readers such as `notion-query-sessions`, `notion-list-session-events`, or `notion-read-session-event` only when needed. Past logs describe past results, not current configuration or authorization.
- A memory-enabled flag does not mean the memory contents were retrieved. Do not guess private internal state.
