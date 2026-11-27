# Discover Custom Agents

The [execution boundaries](../SKILL.md#execution-boundaries) apply throughout.

## List accessible agents

Inspect the current MCP connection for Agent listing or search capabilities. Ordinary page-search results are not an Agent catalog. If listing is unavailable, state that limitation. Configuration retrieval for an already specified target can proceed without a listing capability.

Enumerate every available scope without a query, for example `favorites` and `workspace` on `notion-search-agents`, under the [pagination rule](#check-retrieval-completeness). Deduplicate by workspace ID and Agent ID while retaining favorite status. Report a failed scope or retrieval limit. A name search alone is not a complete catalog.

Describe the list as the scope discoverable through the current connection. Return available names, descriptions, URLs, favorite status, and discovery sources. Do not claim coverage of inaccessible private Agents or other workspaces.

Distinguish listing visibility, instruction access, settings access, edit permission, and write permission for task destinations. Report enabled state only when returned metadata establishes it. Listing does not require reading every Agent's business sources or execution history.

## Check retrieval completeness

Resolve the relationship between a Notion database and its data sources and retrieve the current schema. For example, fetch a returned `collection://` URL when the connection supports it. Check whether SQL, row queries, saved views, or block readers are available and how they behave. A connection without SQL can use another method that enumerates the same scope. Read page content to recover links or formatting omitted by structured search. Do not overwrite a page from a result with truncation, unknown blocks, or unread child blocks as though it were complete.

Paginate to completion when the task covers all records. Saved-view counts and top search results are not complete inventories.

For a reader that returns a cursor, keep reading until it reports no more records: `has_more` false, or no next cursor from a reader without such a flag. An empty or short page that still carries a cursor is not the end. A cap such as "up to 60 runs" counts records, not calls. If the reader says more records exist but gives no cursor, or returns a cursor it already returned, stop and report that scope as partially read.

Use the source procedure's timezone and interval boundaries. Distinguish Slack channel history from thread replies and retrieve replies separately when necessary.

### Check consistency across pages

Cursor exhaustion proves pagination ended, not that the records form a complete snapshot. Determine whether the source procedure needs a result as of one point in time. If it does not say so, treat the scan as live; do not silently replace live semantics with a snapshot. A live scan still watches for records that shifted between pages, such as a repeated ID: reconcile the affected records, or hold the writes and checkpoints that depend on them. Inspect the connection's documented snapshot, cursor, ordering, cutoff, and modification-time guarantees. Unknown guarantees remain unknown: a timestamp filter alone does not freeze membership or values.

Where supported and needed, fix the target IDs or use a stable boundary, detect duplicate IDs and changes, and reconcile affected records. Deduplication alone cannot recover omissions; fixed IDs alone do not freeze values or recover deleted records. A repeated scan without a documented consistency guarantee is not proof of a snapshot. Use only capabilities the connection actually exposes.

Report pagination completion separately from coverage and consistency. If required consistency cannot be established, identify the affected scope as unverified; do not claim complete retrieval or an exact aggregate for it. Hold dependent writes and checkpoints, while continuing independent work unless the source procedure requires stopping the run. For a live traversal, describe the observed scope and changes in the run report, not in content written to the procedure's destinations, without claiming a point-in-time total. Do not keep rescanning without a finite reconciliation rule.

Distinguish partial retrieval, access denial, and a valid empty result. Stop writes and checkpoint updates that depend on missing required information. Stop the entire run if the source procedure requires it. Otherwise continue independent work and record unfinished items.
