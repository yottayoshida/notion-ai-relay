# Pagination consistency evaluation

These synthetic cases test the assistant's decisions from supplied retrieval transcripts. They do not test a real MCP server, prove a service's cursor semantics, or establish compatibility across clients. Production guarantees must come from the actual connection.

The runtime rule is in [Check consistency across pages](../../references/execute-via-mcp.md#check-consistency-across-pages). Do not load this evaluation document or fixture expectations as runtime instructions.

## Cases

[Fixtures](cases.json) cover insertion, deletion, reordering, a documented snapshot, an authorized live traversal, fixed IDs with a modification cutoff but mutable values, and a procedure that states no point-in-time requirement, with and without records shifting between pages. The insertion case also checks that an unrelated task continues while dependent writes and checkpoints are held.

Each case contains the source procedure, connection guarantees, a chronological synthetic transcript, expected decision fields, and a qualitative review criterion. Mutations describe test events, not an additional service capability or permission to reconstruct historical values from a test oracle.

## Run

Use an explicitly authorized model execution and record the model, thinking level, source revision or content hashes, cost, and completion status. Run with no real service connections, credentials exposed to tools, or writable external tools. Give the assistant `SKILL.md` and `references/execute-via-mcp.md` as instructions. For each case supply only `id`, `procedure`, `input` (when present), `connection`, and `transcript`; withhold `expected` and `review`.

Ask the assistant to decide the next action, not perform the writes:

> Apply the supplied Skill to each independent case. No further retrieval capabilities are available. Return a JSON array with one object per case: id, pagination_complete, snapshot_verified, exact_total (null when not verified), hold_dependent_state (whether the retrieved data requires holding dependent writes and checkpoints, apart from any go-ahead they wait for), independent_result (null if none), observed_ids (when requested), planned_write (the exact text of the procedure's dependent write if the retrieved data supports making it now, whether or not it still waits for my go-ahead, else null), and a short explanation of the next action and evidence limitations. Report what is verified; do not claim a planned write has succeeded.

Compare every field in `expected` with the corresponding result; require all cases exactly once. Also review the explanations against `review`: matching booleans alone can hide an unsupported exact count, unnecessary refusal of live work, invented capabilities, or a claim that a write already occurred. Missing cases, malformed responses, timeouts, and skipped cases are failures, not passes. Preserve raw inputs and responses outside the repository and summarize evidence with the change submission.

This is a focused decision evaluation, not an end-to-end write, checkpoint, retry, or concurrent-service test. Static JSON/link checks do not establish model adherence. A prior successful run does not validate subsequent instruction changes.
