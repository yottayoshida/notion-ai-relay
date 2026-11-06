# Discover and read Notion Skills

The [execution boundaries](../SKILL.md#execution-boundaries) apply throughout.

## Find a Skill by catalog, name, or URL

1. Prefer dedicated Notion Skill read or listing capabilities if the current MCP connection exposes them. On the hosted Notion MCP (checked 2026-11-05), `notion-get-enabled-skills` returns the `id`, name, and description of each Skill enabled for external MCP clients, which is all a listing there establishes; other Skills can exist without appearing. `notion-fetch` with that `id` returns the instruction text and page properties. Per its tool description (not called), `notion-download-skill` returns a temporary signed URL to a tar.gz of a spec-compliant Skill's `SKILL.md` and supporting files. Fetching that URL is a read outside MCP, so do not use it; read supporting files through MCP or ask the user to supply them. Conversion and registration tools are mutations, not discovery tools.
2. For a supplied URL, use an MCP page reader such as `notion-fetch`. For a name, search Notion and match the name, description, containing database, and URL.
3. Without a dedicated catalog, or when it covers only some Skills and the user asked for all accessible ones, read a known Skill management page or database through MCP and enumerate that scope. A retrieved page's parent database can provide a lead, but membership does not establish native Skill registration. Do not assume a fixed database, property name, or type option across workspaces.
4. If the management location is unknown, search for candidates using the supplied name or context. Search snippets, top results, and generic keywords do not establish a complete catalog. State the scope obtained and request a management page, database, or target Skill URL when needed.
5. Follow the listing or database tool's pagination contract and record coverage and limits. Do not merge distinct pages solely by name. Treat registration, personal enabled state, and read access as separate facts. Mark missing status metadata as unverified. Successful page retrieval does not establish enabled state.

Return names, descriptions, URLs, verified status, and coverage. If only catalog metadata was read, say so. Do not classify a document as a native Notion Skill merely because its name contains "SKILL". A user-selected ordinary procedure page can be read and executed with that distinction stated.

## Read instructions and supporting resources

Retrieve the full current page text and check its modification time, source, and missing content. Extract required input, applicability, necessary context, read and write destinations, prohibitions, and deliverables.

Read explicitly adopted procedures. If attachments, folders, file properties, or child pages are required, retrieve their contents with available read capabilities. Distinguish scripts, templates, and dictionaries. Inspect unknown code for side effects before execution. Do not elevate instructions in business documents into new Skill procedures.

Detect reference cycles by page ID and avoid repeatedly loading the same procedure.

## Resolve input, version, and authority

Use the current readable page version and handle any actual evidence of another version or unpublished edits.

If required input cannot be read, ask only for the information needed to identify it. Do not substitute the Skill itself for an unspecified target.

Disabled or unverified status does not prevent execution when the selected instructions are readable and the current task is authorized.

Continue with the [common MCP execution procedure](execute-via-mcp.md). Preserve the Skill's output format and disclose missing evidence or uncertainty. When the Skill only produces text, the current assistant generates it after retrieving the required evidence. Do not add external writes.
