# Dependency provenance execution results

Executed 2026-11-16 against base `687e9dfd1d9ebfd7d18af6912e5a521bd7603c81` plus issue #25 working-tree changes in `SKILL.md` and `references/execute-via-mcp.md`. The final runtime files and case inputs were frozen before execution and verified unchanged afterward.

## Final candidate

Pi SDK 1.5.2, inherited `openai-codex/gpt-6.1-sol`, thinking `medium`. Each case used a separate fresh in-memory session. The three follow-up questions ran in their own case's existing context, not a new run, with no additional tool calls. The reader exposed frozen runtime sources only; the synthetic MCP tool returned fixture metadata and mutated only fixture state. No extensions, prior sessions, other agents, shell, or live connections were exposed.

| Case | Observed result | Status |
|---|---|---|
| dependency-a | Exact initial output `score=4`; subsequent provenance identified procedure-v1, code-a and template-v1, their individual modification times or null, and retrieval time. Zero mutations. | PASS |
| dependency-b | Identical parent-v1 and procedure-v1; only comparison code changed. Exact initial output `score=5`; subsequent provenance identified code-b with its own modification time, not the parent's time. Zero mutations. | PASS |
| unknown-and-data | Exact dry-run output `score=4`; code/template revision and modification time stayed null. No adoption or retrieval of the incidental business-data link, no business input in the instruction-dependency list, no mutation or state save. | PASS |
| resume-changed-code | Report distinguished unchanged parent-v1 from code-a → code-b; recomputed pending page-B from planned 4 to 5, performed exactly one update and read it back. Verified independent page-A was not replayed; no other effects. | PASS |

All four read the Skill and the complete common execution reference containing the new rule. They completed in 7, 7, 6 and 8 turns respectively, each within the fixed 16-turn / 240-second limit. Zero skips, timeouts, retries, compactions, or missing usage in the final run. Metadata/effect/output assertions passed; the resume report was also checked manually. Estimated final-run cost: **USD 0.131466**, from SDK usage, not a bill.

The metadata grader was checked before model execution with correct JSON and an acceptable fenced representation, wrong parent revision/time substitutions, prohibited effects and missing readback: 16 non-model checks passed. Expectations were not changed after seeing results.

## Initial attempt and correction

The initial candidate placed the same dependency rule in `references/read-configuration.md`. Two Skill cases produced the expected outputs/metadata but never read that file; they were recorded as failures, not passes. A third case passed. The resume case read the rule and updated isolated page-B to 5, but the provider returned `Our servers are currently overloaded` before readback and a final report. That incomplete attempt is not counted as success or as evidence of a product failure to read back.

The identical rule was moved to the common execution reference, already required by both Agent and Skill paths, and the Skill link was updated. With explicit user permission, all four cases were rerun once against the final candidate. The only read-coverage assertion change followed the rule's new location; fixture inputs and output/metadata/effect expectations were unchanged. The first attempt's records were preserved. No automatic retry or alternate model was used.

Initial reported usage totals USD 0.1068972, including USD 0.0280128 reported before the interrupted attempt. Its remaining cost is unknown, not zero. Thus known reported usage across both execution batches is **USD 0.2383632**; the complete total is unknown. Separate review/main-conversation costs are not included here.

## Reproduce and limits

Use [the replay procedure](README.md) and `cases.json`, preserving the two-turn structure where specified. Obtain the candidate runtime files from the revision being evaluated, not a previously successful run. Record content digests and actual usage outside the distributed repository.

These are bounded synthetic executions, not live MCP transport or client autoload tests. No real Notion metadata, accounts, business data or persistent resume store was read or changed. There is no claim of pre-change failure, improved success rate, repeatability or OS sandboxing. Arithmetic functions and templates are small fixtures, not proof of arbitrary comparison-code equivalence. No reference content was permanently saved by the tested assistant; evaluation snapshots and logs were saved separately by the harness.
