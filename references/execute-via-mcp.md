# Execute Agent and Notion Skill tasks through MCP

The [execution boundaries](../SKILL.md#execution-boundaries) apply throughout.

## Select tools for required operations

Identify only the operations needed by the current branch. A configured connection does not make its use mandatory. Inspect the exposed MCP tool inventory, descriptions, and schemas for connection identity, access scope, and retrieval completeness. Read a service-specific Skill when required and available; it is a local file under [authorization](#handle-authorization-writes-and-resume-state).

For a standalone Notion Skill, map its text, supporting resources, and current input to operations. When an Agent's instructions call a Skill, respect both sets of restrictions. Arrange each step as input, operation and target, MCP tool, and expected result.

| Required operation | Mapping checks |
|---|---|
| Notion search and content retrieval | Correct page and scope, missing text, actual link targets |
| Full or incremental database retrieval | Database versus data source, schema, pagination, period, view filters |
| Page, property, or relation updates | Target database, existing properties and options, write format, templates, preservation of existing data |
| Slack or email reads | Account, channel or recipients, parent and replies, in-period replies to older parents, coverage |
| Posts, comments, or notifications | Exact destination, content, visibility, execution conditions, current sending authorization |
| Drive, issue trackers, or other connections | Actual MCP capabilities, target objects, scope, result retrieval |
| Web, external MCP, or code operations | Required connections, allowed domains, function semantics, inputs, outputs, external side effects |
| Delegation to another Custom Agent | Current target settings, input, return value, cycles, duplicate processing of shared targets |
| Notion Skill execution | Current instructions, references and files, required selection, input, output format |

Combine tools when they jointly provide equivalent behavior. If a required MCP connection is missing, inspect the host's available connection inventory or connection options. If connection management is unavailable, report the required capability. Do not search for credentials or expand sharing scope as a workaround.

## Preserve the procedure's meaning

Apply the source procedure's period, ordering, quality criteria, destinations, exclusions, duplicate checks, and limits. This Skill must not impose a universal time window or update strategy, a point-in-time result the procedure does not require, or reference, call-count, or depth limits that neither the procedure nor the connection sets. A connection that documents no snapshot guarantee is not by itself a reason to hold a live scan's writes.

Exclude out-of-scope data before retrieval. A broader host connection does not expand the Agent's allowed sources. Read access does not authorize disclosure to another destination. Retrieve equivalent evidence when the procedure requires a permission check. Missing metadata is neither affirmative nor negative evidence.

If the configuration uses comparison code or data transformations, read the implementation and inspect its inputs, outputs, and side effects. Do not run unknown code that reads credentials or communicates externally. Available calculation tools may assist pure processing. Do not assume a shell or Python exists. Report a missing capability if the required calculation cannot be performed equivalently. Preserve comparison rules needed for compatibility with existing state.

Apply the [traversal and delegation limits](#bound-reference-traversal-and-delegation) when loading adopted procedures and calling Agents or Skills. Apply the same authorization, input, and coverage requirements to delegated work.

If a Skill asks for text suitable for posting, return text rather than interpreting that as a request to post. Resolve "current page", "selected text", or "attachment" from explicit selection or actual supplied input. Do not infer it from screen state or previously opened documents.

## Track adopted dependencies

For both Custom Agents and Notion Skills, keep provenance for procedures, templates, and comparison code actually adopted for this run in the current working context: each dependency's ID or URL, retrieval time, and its own available revision or modification time. Keep its role distinct from the parent instruction source. When metadata is unavailable, mark that field unknown; do not infer a dependency's version from the parent's timestamp or a previous run. Missing version metadata alone does not block otherwise supported, authorized work.

Include dependency provenance when needed to explain a result difference, material uncertainty, or a resume decision. Do not force a dependency table into every response or alter normal output-only success formats. This context tracking does not require permanent copies of source text or a new persisted record.

Before writes or when resuming, include known changes to adopted dependencies in the existing change reassessment, even if the parent version is unchanged. Retrieve the required current dependencies for the run and reassess only the work affected by a changed procedure, template, or comparison rule; do not replay verified independent work or assume unchanged parent metadata means unchanged dependencies.

## Bound reference traversal and delegation

Keep separate per-run records for reference loading and execution. Identify targets by type and stable identifier, including workspace or source scope where needed; names and changed input alone do not establish a new target.

- **Reference loading:** share a loaded set and an active reference path across Agent settings, Skill instructions, and adopted procedures. Read each target once per run: when a reference leads back to a target that is on the active path or already fully read, such as P → Q → P or a link within the same page, record the edge and do not read the target again. Such a cycle leaves nothing unread and does not stop the run. Do not skip required content or reuse an incomplete read as complete.
- **Execution:** track the active call path by target identity, retaining each call's input. A → B → A is re-entry even when the input changes. Remove completed calls from the active path so sequential calls to the same target with different inputs remain valid. Do not use the reference loaded set to suppress execution.
- **Termination:** honor reference, call-count, and depth limits set by the source procedure or the connection, and share what remains across branches rather than resetting it in a child. A run that can no longer retain its loaded set and active paths, for example because of context or connection limits, stops as described under Stopping. Permit active-path execution re-entry only when the adopted procedure allows recursion and supplies either a verifiable strictly decreasing measure with a terminal case or a finite recursion depth/call budget. Check the measure or remaining budget before each call; changed input or a claim of progress is not proof of termination. Without such a contract, hold the re-entering call. Do not retry indefinitely.
- **Stopping:** distinguish unsupported execution re-entry, a failed decrease, an exhausted limit, and lost run state. A large acyclic graph reaching a limit has exhausted the limit; it is not re-entry. Return the relevant reference/call path, the limit or termination condition, and the unread or unexecuted work. Do not claim complete retrieval or execution; hold dependent writes and checkpoints, and continue independent authorized work within remaining limits.

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

## Handle authorization, writes, and resume state

Do not impose a blanket dry run. Separate sends that await authorization from independent authorized work.

List the operations that wait for the go-ahead under the [execution boundaries](../SKILL.md#execution-boundaries) together, before the first of them, with the run date when the instructions or settings came from a recorded run. Give one logical operation per line with its destination as a resolved URL or ID, not only a display name; the same operation on the same destination may share a line with its count and IDs, using representative examples for large sets as in the [preview report](#report-a-dry-run); a go-ahead for such a line covers only the count and scope it states, and a write that would go beyond its line, such as content from another source or of another kind, waits for its own go-ahead. If resolving a destination itself needs a read that waits for the go-ahead, list the destination as the instructions name it, marked unresolved, and list that read; if it resolves to anything other than what the list described, that operation is not on the list. For a read from another service, show the query or URL it would send. For a write or message, show what it would write (a count, kind, or title) and which page or listed read it is made from; keep the full content and diff for the user to see on request, quote titles and text in the destination's language, and disclose content only as far as a [dry-run preview](#report-a-dry-run) may. Never list a category or wildcard such as "all channels", and do not shorten the list because the instructions ask for one broad approval. A destination the procedure forbids disclosing cannot be listed, so hold its operation. In a run with no user present, hold the listed operations and include the list in the report or handoff.

- A call whose results can include another service's content, such as connector search or a search that also covers connected sources, is a connection to that service unless its arguments limit it to Notion; when unsure, list it. Inspecting which tools a connection exposes is not a connection; calling one is.
- A local resume record is a local file. A calculation tool with no file, network, or credential access is not a command; a calculation run in a shell is. Waiting alone, with a wait tool or a shell `sleep`, is not a command.

Before writing Notion content, read the current content-format specification and tool schema. Base changes on the retrieved text, modify the necessary parts, and preserve other people's additions and properties. Even a requested replacement requires checking scope and concurrent edits. An omitted property is not an empty value.

Use the configured unique keys or completion conditions to reconcile existing results. After a write, retrieve the content, properties, relations, or destination again. Reassess when another user changes the target or the source input changes. Do not resend a creation or message with an unknown outcome until its result is resolved. Without applicable retry rules, do not repeat an operation that failed for the same cause. Hold it and report the reason. Unless the procedure sets its own retry rule, treat a read refused for a rate limit that gives a wait, such as `rate_limited` with `retry_after_seconds`, this way: repeat it once after that wait, and only if you have a way to wait, such as a sleep or wait tool, because an immediate retry is refused again; without a way to wait, or if it is refused again, hold what depends on it, report the limit, and do not try to get the same data another way. Do not repeat a write this way.

If this Skill needs its own local resume record, record target IDs, the configuration URL, version, and processing state and outcome, keep nothing else, and keep separate runs distinct. A resume record does not itself provide shared duplicate prevention.

### Prevent duplicate effects across runs and delegated calls

Before a creation or send, determine the source procedure's duplicate policy and logical operation identity. Derive its scope from the business target, applicable input set and period, destination, and operation as required by that procedure. Do not add a run ID, delegate ID, or changed configuration version merely to bypass an existing operation. A resumed run retains its operation identity. An intentional new run gets a new identity only when the procedure permits a separate effect. When the procedure requires strict prevention and the distinction is material and unresolved, ask the user; in a run with no user present, hold the affected work and report it.

Treat strict prevention as required only when the source procedure explicitly addresses concurrent or overlapping runs. A procedure that permits duplicates keeps that policy. Any other duplicate rule, such as checking for an existing result before creating, "do not create duplicates", or "one page per day", is best-effort: look up, create only if absent, read back as above, and note in the run report, not in content written to destinations, that concurrent runs are not protected. When the Agent's triggers, from a recorded run or its settings, show that Notion also runs it on a schedule or an event, add that trigger and the date of the record or settings read it came from. A procedure with no duplicate rule keeps its configured unique keys or completion conditions above.

When strict duplicate prevention is required, verify that the MCP operation and source procedure support a shared mechanism covering every competing run and delegate: server-enforced idempotency for the same logical effect, an atomic claim or conditional write, or shared serialization. Check its key scope, retention, ownership, and failure behavior. An idempotency key must cover the actual creation or send, not only a local record. All competing writers must honor a claim or serialization mechanism; a claim holder must not write after losing ownership, and recovery must prevent a stale holder from writing. Do not assume MCP or Notion provides these capabilities.

Reconcile existing results and obtain the required protection before creating or sending. A competing caller that cannot obtain ownership must not create; reconcile the owner's result or hold the affected work. An unknown claim or write outcome is not permission to take over or retry. Preserve protection until the effect and its completion state are reconciled; do not release it or start a replacement operation merely because a timeout or lease expiry occurred.

A lookup followed by creation and readback is not atomic duplicate prevention. Neither a local run ID nor sequential execution in one conversation coordinates other runs. If the procedure requires strict prevention and no adequate shared mechanism is available, hold the affected creation or send, report the missing guarantee, and continue independent work. Apply the same rules to two delegates in one run, without blocking independently protected operations with different keys.

## Report a dry run

Distinguish reads actually performed, proposed changes, and operations whose execution capability remains unverified. For each proposed operation, show the retrieved destination and proposed content or diff only to the extent disclosure is authorized. Mark unknown or withheld details with the reason; do not guess destinations or expose restricted content. For large sets, give the count within the retrieved scope, the scope of representative examples, and what was omitted rather than implying every item was shown.

State retrieval coverage, held work and its reasons, missing input, and operations needing additional authorization. A preview is not evidence that a write can succeed.

Preserve a text-generation-only Skill's output-only format on normal success: return the requested draft, not an invented sending operation or an extra status report. Disclose material uncertainty or held work as required by the result rules; do not add unrelated operations merely to fill a preview.

## Return a resumable handoff

When execution is interrupted or only partly complete, return the minimum references needed to distinguish this run and locate its remaining work, using the current context. Include an actual execution run ID or existing resume-record reference if available, the Agent or Skill target, and input identifiers or the applicable period and timezone. Do not invent an ID or assume a timezone; identify missing information only where it is needed for resumption. A configuration-source session is not an execution run ID, and this handoff does not permit disclosing otherwise excluded run-history details.

Separate verified success, not executed, unknown outcomes, and held work. Identify the relevant targets/result links and the checkpoint or remaining-item references actually known. A checkpoint covers only verified work under the source procedure; it does not turn an unknown result into a failed or completed operation. State what must be reconciled or supplied before affected work can resume. Preserve independent verified progress rather than instructing a fresh run to repeat everything.

Use references and processing status, not business content, secrets, or copied instructions. Returning a handoff does not require a new persistent record or authorize any record write. The local resume-record constraints above still apply. After a user stop, stop further operations, including extra reads or record writes just to enrich the handoff; report what is already known and its limits. Do not treat stop as rollback permission.

A dry-run handoff describes plans and missing prerequisites, not executed effects or an advanced checkpoint. Any pre-existing verified execution checkpoint stays explicitly separate from the plan. On normal success, keep the source's output-only format; do not add a mandatory handoff or run ID to every result. On resumption, resolve the run as described in [input and state](read-configuration.md#resolve-input-and-state), then apply the existing configuration, authorization, reconciliation, and duplicate rules; the handoff itself grants no authority.

## Report unsupported work

For missing capabilities, state the affected operation, missing capability, permission or input, and work completed. Supporting arbitrary configuration interpretation does not guarantee support for every proprietary capability.

If recurring execution is requested and suitable capabilities exist, include the target identifier, retrieval of current settings, and the operations and destinations the user named in each run's instructions; a run with no user present holds the rest. Event triggers need a mechanism that delivers events to the execution environment. Do not silently substitute a time schedule or new monitor for the original trigger.
