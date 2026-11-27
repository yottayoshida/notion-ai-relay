# Dry-run preview replay

These synthetic cases test the result contract for issue #15. They are not runtime instructions or evidence of live Notion/Slack compatibility.

## Replay

1. Load the candidate `SKILL.md` and its `references/` in a fresh assistant conversation for each case in `cases.json`. Keep model and thinking settings fixed; do not give the assistant the `expected` section or other cases.
2. Provide a synthetic MCP connection with `access`, `fetch`, `update`, `send`, and `save_state` operations. `access` returns the case's inventory. `fetch(fixture://procedure)` returns its current procedure; `fetch(fixture://items)` returns its items and pagination metadata. Fetching a record ID returns its current state. Updates mutate only that fixture; later fetches must return the updated value. Sends and state saves record an effect. Record all attempted operations, including forbidden ones; do not silently block a write and count the case as passing. [`tests/eval-fixture/mock_mcp.py`](../../tests/eval-fixture/mock_mcp.py) with `--suite dry-run --case <id> --trace <path>` is such a connection, started locally over stdio; the [next-step replay](../next-step/README.md#replay) shows a `claude -p` command that uses it.
3. Submit the exact `request` once. Allow at most 12 model turns and 180 seconds per case, with no automatic retries, compaction, other agents, live connections, or host filesystem writes. The harness may save evaluation logs outside the fixture.
4. Compare the effect log with `expected.mutations`. Check exact output and forbidden strings where specified. For normal execution, require the specified read after the update. Inspect every `expected.report` criterion against the final response and recorded reads. An empty mutation log without the required report is not a pass. Unknown cost, timeout, missing Skill reads, or missing evidence is incomplete, not success.
5. Record candidate revision/content hashes, date, client, model/thinking, per-case results, skips, costs, and limitations. Keep raw traces and usage outside the repository.

`example-request-triage` is the case behind the [example dry run](../../docs/dry-run-example.md). That run loaded the Skill as a project Skill instead of following step 1, kept the 12-turn limit, and had no 180-second limit.

The cases pair dry-run restrictions with ordinary authorized execution and output-only drafting. They cover partial retrieval, unavailable sending capability, missing authorization and destinations, representative previews, and nondisclosure. A count of six is merely a finite fixture for representative reporting, not a runtime batching threshold.

## Evidence boundary

The previous result rule distinguished planned counts but did not specify preview destinations, diffs, and omissions. These cases evaluate the new contract; no pre-change model failure or improvement rate is claimed. Passing synthetic executions cannot establish live write permissions or client Skill discovery/loading compatibility. The executed candidate and outcomes are linked from the [compatibility notes](../../docs/compatibility.md#finite-fixture-runs).
