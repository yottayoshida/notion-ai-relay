# Collection consistency fixtures

Cursor exhaustion establishes the end of a scan under the connection's contract, not necessarily a complete collection at one instant. The runtime rules are in [Check collection consistency](../references/execute-via-mcp.md#check-collection-consistency).

## Cases and expectations

[The repository-only fixtures](https://github.com/yottayoshida/notion-ai-relay/blob/main/tests/collection-consistency.json) use fictional IDs and integer amounts. Each scan has two pages and an explicit query contract. Mutation notes and expected outcomes are scorer-only; they are not supplied to the model. The model retrieves the procedure, schema, and actual page responses through three in-memory MCP simulator tools.

| Case | Source procedure and connection | Required behavior |
|---|---|---|
| `insertion` | Single-revision total required; a new row falls before the live cursor | Do not certify the collection or total; hold aggregate and checkpoint writes |
| `deletion` | Single-revision total required; deletion shifts a live offset past a row | Same; terminal pagination is insufficient |
| `sort-reorder` | Single-revision total required; mutable ordering repeats B and skips C | Same; deduplication cannot establish missing membership |
| `pinned-snapshot` | Both IDs and values are pinned to s1/r1 while the live source changes | Verify total 100, publish the snapshot result, verify it, then advance and verify the checkpoint |
| `intentional-live` | First observed amount per distinct ID; no point-in-time requirement | Verify observation total 100, label it live, and advance only the live scan checkpoint; do not substitute a snapshot or count B twice |

All cases also require an independent control read, receipt write, and read-back. Holding the collection-dependent work must not block that task. The simulator accepts and records every write attempt, including an incorrect aggregate or premature checkpoint: a passing hold is a model decision, not a host-side write filter.

The final JSON describes the collection deliverable. An unverified total must be null; its `semantics` may describe either the requested snapshot or the observed live scan. A verified result must use the procedure's requested semantics. Full reasons remain available for human inspection.

## Run with explicit model authorization

This is an opt-in behavioral test, not an automatic CI job. It uses the Pi SDK and the configured provider's normal authentication interface. Each case creates one fresh in-memory session, potentially with several model turns for tool calls. Obtain permission for the case executions and associated model usage before running. Inherit the operator session's provider, model, and thinking level rather than selecting another model.

Use Node compatible with the installed Pi SDK (this runner uses Pi 1.5.2's SDK interface). Set the SDK package root and the inherited configuration explicitly:

```sh
export PI_SDK_ROOT=/path/to/node_modules/@earendil-works/pi-coding-agent
export RELAY_PROVIDER='<current provider>'
export RELAY_MODEL='<current model ID>'
export RELAY_THINKING='<current thinking level>'
node tests/collection-consistency.mjs --run /path/to/workspace/artifacts/new-collection-run \
  insertion deletion sort-reorder pinned-snapshot intentional-live
```

No global settings are changed. Resource discovery is replaced: only the four repository runtime instruction files and three simulator tools are exposed, with no built-in file/shell tools, external MCP connection, or extensions. The runtime instruction files are supplied as loaded text; this does **not** test client Skill discovery or loading. No real Notion objects are read or changed. Simulator writes exist only in memory.

The runner disables automatic retries and compaction, caps each case at 240 seconds and 40 executed tool calls, and stops on a failed assertion. It refuses an existing trace path rather than silently rerunning a case. A failure leaves a trace and exits nonzero; do not automatically retry paid cases. Unreached cases are not passes. Each output trace includes prompts, tool inputs/results, completed messages, usage, source hashes, model, thinking, timestamps, and settlement state. Keep these raw execution records outside the repository.

## Score existing traces without model calls

```sh
node tests/collection-consistency.mjs --score /path/to/workspace/artifacts/new-collection-run/*.json
```

Scoring checks the final status and total, verified-result semantics, pagination, required reads, exact write targets and values, read-after-write, and aggregate verification before a checkpoint. It accepts a known destination's `not found` response before creation, but requires read-back content to equal the written value. Other tool errors, timeouts, unsettled runs, and automatic recovery are rejected. Inspect the recorded explanation as well: assertions do not establish every possible natural-language claim.

These finite synthetic cases are evidence about model behavior under the supplied contracts, not a guarantee of future compliance, a live Notion pagination experiment, or broad client compatibility. They do not test reconstruction of deleted rows, historical values, or a working change-feed reconciliation algorithm. Passing revised instructions alone does not show an improvement over older instructions; compare observed results without inventing a pre-change defect.
