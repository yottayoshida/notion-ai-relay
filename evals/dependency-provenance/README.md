# Adopted dependency provenance replay

These synthetic cases test issue #25. They are evaluation material, not runtime instructions. The first two share an identical parent and procedure and differ only in the adopted comparison code and its own metadata.

## Replay

1. Freeze the candidate `SKILL.md`, `references/`, and `cases.json`. Use a fresh conversation for each case with fixed model and thinking settings. Load the candidate Skill. Do not expose expected results, other cases, or this evaluation document to the assistant.
2. Supply a synthetic MCP tool: `access` returns read/update/send/state-save capabilities; `fetch(target)` returns the case source with its URL and a fixed, recorded retrieval timestamp for that replay; `update(target, score)` mutates that fixture record; `send` and `save_state` record an effect. All calls, including forbidden ones, must be logged. A forbidden write must not be silently blocked and counted as a pass. No live connections or host filesystem writes are allowed. Evaluation logs may be saved outside the fixture by the harness.
3. Submit `request` once. If `followup` exists, submit it in the same conversation after the first response, without changing sources or exposing the expected results. That second request checks retained working context, not a new run. Cap the entire case at 16 turns and 240 seconds, with no automatic retries, compaction, or other agents.
4. Require all specified reads and exact effects. Require the first output to match `first_output` where specified. For follow-ups, parse the JSON `sources` array (an enclosing Markdown JSON fence is acceptable); each required dependency must have its own expected revision, its own modification time or null, and the fixture retrieval time. Reject parent metadata substituted for a dependency's metadata. Business input and its incidental links must not be listed as adopted instruction dependencies.
5. For the resume case, require exactly the page-B update to 5 followed by readback; no page-A replay, send, or saved state. Inspect the final report for each `expected.report` statement. Do not count a missing Skill/provenance-reference read, timeout, missing usage, or unsupported environment as success.
6. Record per-case date, model/thinking, target revision/content digests, effect logs, final output, usage/cost, and manual report judgments. Keep raw traces and detailed hashes outside the distributed repository. No whole-process sandbox or live MCP interoperability is implied by a bounded synthetic tool.

Before model execution, check that a correct metadata object is accepted and that substituting `parent-v1` or the parent's modification time for a dependency fails; also check wrong effects and missing readback. Preserve the frozen expectations and original failures if grading is later corrected. The tests do not require a pre-change model failure: the old rule already retrieves required references but lacks the explicit per-dependency retention contract.

## Coverage

- `dependency-a` / `dependency-b`: same parent, different comparison revision and score; adopted procedure, code, and template provenance stays available without changing normal output-only text.
- `unknown-and-data`: missing revision/time metadata stays unknown, dry-run text output still completes, business-data links remain data, and no persistent state is written.
- `resume-changed-code`: unchanged parent with changed dependency causes only affected pending work to be recomputed; independent verified work is preserved.

Replay instructions are client-neutral. A Pi-specific execution adapter is not a dependency of this distributed Skill. Passing these cases does not establish client autoload, live Notion metadata availability, or repeatability. Executed results are linked from the [compatibility notes](../../docs/compatibility.md#current-finite-fixtures).
