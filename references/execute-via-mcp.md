# Execute Agent and Notion Skill tasks through MCP

The [execution boundaries](../SKILL.md#execution-boundaries) apply throughout.

## Select tools for required operations

Identify only the operations needed by the current branch. A configured connection does not make its use mandatory. Inspect the exposed MCP tool inventory, descriptions, and schemas for connection identity, access scope, and retrieval completeness. Read a service-specific Skill when required and available.

For a standalone Notion Skill, map its text, supporting resources, and current input to operations. When an Agent calls a Skill, respect both sets of restrictions. Arrange each step as input, operation and target, MCP tool, and expected result.

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

Apply the source procedure's period, ordering, quality criteria, destinations, exclusions, duplicate checks, and limits. This Skill must not impose a universal time window or update strategy.

Exclude out-of-scope data before retrieval. A broader host connection does not expand the Agent's allowed sources. Read access does not authorize disclosure to another destination. Retrieve equivalent evidence when the procedure requires a permission check. Missing metadata is neither affirmative nor negative evidence.

If the configuration uses comparison code or data transformations, read the implementation and inspect its inputs, outputs, and side effects. Do not run unknown code that reads credentials or communicates externally. Available calculation tools may assist pure processing. Do not assume a shell or Python exists. Report a missing capability if the required calculation cannot be performed equivalently. Preserve comparison rules needed for compatibility with existing state.

Apply the [traversal and delegation limits](#bound-reference-traversal-and-delegation) when loading adopted procedures and calling Agents or Skills. Apply the same authorization, input, and coverage requirements to delegated work.

If a Skill asks for text suitable for posting, return text rather than interpreting that as a request to post. Resolve "current page", "selected text", or "attachment" from explicit selection or actual supplied input. Do not infer it from screen state or previously opened documents.

## Track adopted dependencies

For both Custom Agents and Notion Skills, keep provenance for procedures, templates, and comparison code actually adopted for this run in the current working context: each dependency's ID or URL, retrieval time, and its own available revision or modification time. Keep its role distinct from the parent instruction source. When metadata is unavailable, mark that field unknown; do not infer a dependency's version from the parent's timestamp or a previous run. Missing version metadata alone does not block otherwise supported, authorized work. Links in business data do not become instruction dependencies merely by being read.

Include dependency provenance when needed to explain a result difference, material uncertainty, or a resume decision. Do not force a dependency table into every response or alter normal output-only success formats. This context tracking does not require permanent copies of source text or a new persisted record; the existing retention and dry-run boundaries still apply.

Before writes or when resuming, include known changes to adopted dependencies in the existing change reassessment, even if the parent version is unchanged. Retrieve the required current dependencies for the run and reassess only the work affected by a changed procedure, template, or comparison rule; do not replay verified independent work or assume unchanged parent metadata means unchanged dependencies.

## Bound reference traversal and delegation

Keep separate per-run records for reference loading and execution. Identify targets by type and stable identifier, including workspace or source scope where needed; names and changed input alone do not establish a new target.

- **Reference loading:** share a loaded set and an active reference path across Agent settings, Skill instructions, and adopted procedures. Read each target once per run: when a reference leads back to a target that is on the active path or already fully read, such as P → Q → P or a link within the same page, record the edge and do not read the target again. Such a cycle leaves nothing unread and does not stop the run. Do not skip required content or reuse an incomplete read as complete.
- **Execution:** track the active call path by target identity, retaining each call's input. A → B → A is re-entry even when the input changes. Remove completed calls from the active path so sequential calls to the same target with different inputs remain valid. Do not use the reference loaded set to suppress execution.
- **Termination:** honor reference, call-count, and depth limits set by the source procedure or the connection, and share what remains across branches rather than resetting it in a child. Do not invent such limits. A run that can no longer retain its loaded set and active paths, for example because of context or connection limits, stops as described under Stopping. Permit active-path execution re-entry only when the adopted procedure allows recursion and supplies either a verifiable strictly decreasing measure with a terminal case or a finite recursion depth/call budget. Check the measure or remaining budget before each call; changed input or a claim of progress is not proof of termination. Without such a contract, hold the re-entering call. Do not retry indefinitely.
- **Stopping:** distinguish unsupported execution re-entry, a failed decrease, an exhausted limit, and lost run state. A large acyclic graph reaching a limit has exhausted the limit; it is not re-entry. Return the relevant reference/call path, the limit or termination condition, and the unread or unexecuted work. Do not claim complete retrieval or execution; hold dependent writes and checkpoints, and continue independent authorized work within remaining limits.

## Check retrieval completeness

Resolve the relationship between a Notion database and its data sources and retrieve the current schema. For example, fetch a returned `collection://` URL when the connection supports it. Check whether SQL, row queries, saved views, or block readers are available and how they behave. A connection without SQL can use another method that enumerates the same scope. Read page content to recover links or formatting omitted by structured search. Do not overwrite a page from a result with truncation, unknown blocks, or unread child blocks as though it were complete.

Paginate to completion when the task covers all records. Saved-view counts and top search results are not complete inventories. Use the source procedure's timezone and interval boundaries. Distinguish Slack channel history from thread replies and retrieve replies separately when necessary.

### Check consistency across pages

Cursor exhaustion proves pagination ended, not that the records form a complete snapshot. Determine whether the source procedure needs a result as of one point in time. If it does not say so, treat the scan as live and do not hold its writes merely because the connection documents no snapshot guarantee; do not silently replace live semantics with a snapshot. A live scan still watches for records that shifted between pages, such as a repeated ID: reconcile the affected records, or hold the writes and checkpoints that depend on them. Inspect the connection's documented snapshot, cursor, ordering, cutoff, and modification-time guarantees. Unknown guarantees remain unknown: a timestamp filter alone does not freeze membership or values.

Where supported and needed, fix the target IDs or use a stable boundary, detect duplicate IDs and changes, and reconcile affected records. Deduplication alone cannot recover omissions; fixed IDs alone do not freeze values or recover deleted records. A repeated scan without a documented consistency guarantee is not proof of a snapshot. Use only capabilities the connection actually exposes.

Report pagination completion separately from coverage and consistency. If required consistency cannot be established, identify the affected scope as unverified; do not claim complete retrieval or an exact aggregate for it. Hold dependent writes and checkpoints, while continuing independent work unless the source procedure requires stopping the run. For a live traversal, describe the observed scope and changes in the run report, not in content written to the procedure's destinations, without claiming a point-in-time total. Do not keep rescanning without a finite reconciliation rule.

Distinguish partial retrieval, access denial, and a valid empty result. Stop writes and checkpoint updates that depend on missing required information. Stop the entire run if the source procedure requires it. Otherwise continue independent work and record unfinished items.

## Handle authorization, writes, and resume state

Do not impose a blanket dry run. Separate sends that await authorization from independent authorized work.

Before writing Notion content, read the current content-format specification and tool schema. Base changes on the retrieved text, modify the necessary parts, and preserve other people's additions and properties. Even a requested replacement requires checking scope and concurrent edits. An omitted property is not an empty value.

Use the configured unique keys or completion conditions to reconcile existing results. After a write, retrieve the content, properties, relations, or destination again. Reassess when another user changes the target or the source input changes. Do not resend a creation or message with an unknown outcome until its result is resolved. Without applicable retry rules, do not repeat an operation that failed for the same cause. Hold it and report the reason.

If this Skill needs its own local resume record, record target IDs, the configuration URL, version, and processing state and outcome, keep nothing else, and keep separate runs distinct. A resume record does not itself provide shared duplicate prevention.

### Prevent duplicate effects across runs and delegated calls

Before a creation or send, determine the source procedure's duplicate policy and logical operation identity. Derive its scope from the business target, applicable input set and period, destination, and operation as required by that procedure. Do not add a run ID, delegate ID, or changed configuration version merely to bypass an existing operation. A resumed run retains its operation identity. An intentional new run gets a new identity only when the procedure permits a separate effect. When the procedure requires strict prevention and the distinction is material and unresolved, ask the user; in a run with no user present, hold the affected work and report it.

Treat strict prevention as required only when the source procedure explicitly addresses concurrent or overlapping runs. A procedure that permits duplicates keeps that policy. Any other duplicate rule, such as checking for an existing result before creating, "do not create duplicates", or "one page per day", is best-effort: look up, create only if absent, read back as above, and note in the run report, not in content written to destinations, that concurrent runs are not protected. A procedure with no duplicate rule keeps its configured unique keys or completion conditions above.

When strict duplicate prevention is required, verify that the MCP operation and source procedure support a shared mechanism covering every competing run and delegate: server-enforced idempotency for the same logical effect, an atomic claim or conditional write, or shared serialization. Check its key scope, retention, ownership, and failure behavior. An idempotency key must cover the actual creation or send, not only a local record. All competing writers must honor a claim or serialization mechanism; a claim holder must not write after losing ownership, and recovery must prevent a stale holder from writing. Do not assume MCP or Notion provides these capabilities.

Reconcile existing results and obtain the required protection before creating or sending. A competing caller that cannot obtain ownership must not create; reconcile the owner's result or hold the affected work. An unknown claim or write outcome is not permission to take over or retry. Preserve protection until the effect and its completion state are reconciled; do not release it or start a replacement operation merely because a timeout or lease expiry occurred.

A lookup followed by creation and readback is not atomic duplicate prevention. Neither a local run ID nor sequential execution in one conversation coordinates other runs. If the procedure requires strict prevention and no adequate shared mechanism is available, hold the affected creation or send, report the missing guarantee, and continue independent work. Apply the same rules to two delegates in one run, without blocking independently protected operations with different keys.

## Report unsupported work

For missing capabilities, state the affected operation, missing capability, permission or input, and work completed. Supporting arbitrary configuration interpretation does not guarantee support for every proprietary capability.

If recurring execution is requested and suitable capabilities exist, include the target identifier and retrieval of current settings in each run's instructions. Event triggers need a mechanism that delivers events to the execution environment. Do not silently substitute a time schedule or new monitor for the original trigger.
