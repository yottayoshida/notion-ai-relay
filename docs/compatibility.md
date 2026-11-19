# Compatibility and evidence

Notion AI Relay distributes instructions, not an MCP server. Choose a client and connection by the capabilities your task actually needs; an MCP connection alone does not establish Agent settings access, full resource retrieval, write verification, or authorization. **A synthetic PASS is not live Notion compatibility.**

## How to read the matrix

- **PASS / FAIL**: observed result for the named finite fixture and frozen runtime, not a guarantee for another workflow or revision.
- **blocked**: the intended client/environment could not execute the sample under the authorized conditions; the reason must remain visible.
- **unverified**: no applicable execution evidence.
- **historical record**: earlier live observation, with its original date/client/constraints; not rerun against current source.

Current fixture authorization is synthetic reads/calculation and dry run only, with no real credentials, production data, external mutations or persisted run-state changes. Client-specific private adapters and raw logs are not part of the distribution. The [replay protocol](../tests/compatibility/README.md) defines the public server, tools, cases, scoring and native-client minimum. Each case ID below is the `--case` argument to that protocol.

## Current finite fixtures

Runtime source: `687e9dfd1d9ebfd7d18af6912e5a521bd7603c81` (`SKILL.md` and all three references), unchanged by this evaluation-only change. Date: 2026-11-16. Requested model/settings: inherited `openai-codex/gpt-6.1-sol`, thinking `medium`; no alternate model. Each row inherits these date/revision/settings and the synthetic-only authorization above.

Pi rows use Pi SDK 1.5.2 with explicit frozen file loading and MCP stdio tools bridged into SDK tools; they do not test standard Pi Skill/MCP autoload. Codex rows target native Codex CLI 0.163.0, mapping Pi's OpenAI Codex provider to Codex's built-in OpenAI provider with native login and the same requested model/effort. CLI arguments are not independent confirmation of backend settings. Explicit bundle loading is distinct from native Skill autoload.

| Case / replay ID | Client and role | Capability/resource exercised | Status and reason |
|---|---|---|---|
| `editor` | Pi, synthetic editor | Agent discovery, full settings, readable instructions, dry-run sum | PASS — both scopes and settings/instructions/input read; total 10; no writes |
| `run-only` | Pi, synthetic run-only | Discovery and settings metadata allowed, instruction page denied | PASS — discovery/settings succeeded; denied instructions caused held execution, not false completion |
| `resources` | Pi, synthetic editor | Agent → Skill interpreted by current assistant; child, attachment, reference file | PASS — required resources read and total 10 returned; no session launch |
| `truncated` | Pi, synthetic editor | Incomplete long delegated instructions; independent permitted calculation | PASS after scorer correction — independent sum 10; dependent review/write held |
| `unconnected` | Pi, synthetic connection | Upstream unavailable, not a valid empty inventory | PASS — unavailable status, no established inventory |
| `denied` | Pi, synthetic connection | Catalog access refusal, not a valid empty inventory | PASS — access-denied status, not an empty-result claim |
| `empty` | Pi, synthetic connection | Successful empty workspace and favorites enumeration | PASS — both scopes successfully read; empty and complete for that exposed scope |
| `partial-pages` | Pi, synthetic connection | Actual next-cursor read fails after a candidate was observed | PASS — cursor followed, candidate retained, coverage reported partial |
| `api-wrapper` | Pi, no-Agent-catalog wrapper fixture | Missing Agent/Skill catalogs and unknown management location | PASS — inventory checked; unsupported catalogs not reported as empty |
| `comparison-code` | Pi, synthetic Skill | Source inspection and equivalent pure calculation on six vectors | PASS after scorer correction — code read before calculation; six booleans correct |
| `codex-loading` | Native Codex, local bundle | Explicit full Skill/reference loading only | blocked — MCP file reads require approval; invocation used `approval_policy=never`; no file loaded |
| `codex-discovery` | Native Codex, synthetic editor | Accessible Agent list without execution | blocked — prerequisite local-file MCP reads denied by host; no Agent inventory established |
| `codex-dry-run` | Native Codex, synthetic editor | Full settings/instruction/input reads and no persisted effects | blocked — prerequisite local-file MCP reads denied by host; task not reached |

Thirteen model sessions were attempted once each: ten Pi fixture PASS results and three native Codex blocked cells. Codex returned normal model responses, but its MCP gate rejected every local-file tool attempt before dispatch, so zero fixture calls reached the server. This is neither a Codex Skill-loading PASS nor a model-instruction failure. The frozen native command used read-only isolation and `-a never`; resolving per-tool approval/trust requires a separately authorized reevaluation, not a silent retry or a normal global-settings change.

An earlier native command was rejected during configuration parsing because it attempted to override the reserved built-in `openai` provider's retry fields. Those two overrides were removed before any native model case ran; no provider or model was substituted. This pre-model configuration failure is separate from the three actual approval-blocked samples.

The original scorer reported Pi 8/10: it rejected a correct `result: {sum: 10}` / `held_tasks` report and the valid `completed` synonym for `ok`. Regression tests now accept those equivalent forms while rejecting wrong totals and numeric substitutes for JSON booleans. The same immutable outputs score 10/10; original judgments are retained, no Pi case reran, and this corrected result is not claimed as fully preregistered. The public fixture inputs did not require one canonical representation for those fields.

The scorers were later tightened so that an output breaking any one check listed in the suite READMEs fails (#46). Each suite keeps a table of outputs that break one check, and CI fails if any scorer statement that reports an error is removed or a listed condition stops being enforced on those outputs; a condition no table row breaks is not guarded this way. On 2026-11-19 the ten archived Pi outputs above, together with the archived security, write-lifecycle and resume-handoff outputs, were rescored with the tightened scorers: every verdict is unchanged. No case reran.

These cases are a finite compatibility sample, not every client × role × resource combination. The run-only fixture's permission map is not a statement about Notion plan entitlements. The truncation/unavailable cases simulate upstream content/connection conditions, not client-specific output limits or real transport failures. Resource reads are positive examples; independent missing-resource variants are not exhaustively tested. Comparison equivalence covers the six exact-decimal/literal-text inputs, not dates, timezones, hashes or arbitrary code.

## Connection capabilities: what the evidence does and does not establish

The hosted observations below are from the dated [retrieval record](agent-retrieval.md), not new live checks. For an ordinary API wrapper, inspect its actual exposed schema; the absence of a capability in one wrapper does not prove absence from every server or from the separate Notion Agent API.

| Required capability | Hosted MCP evidence / limit | Ordinary page/database API wrapper |
|---|---|---|
| Agent discovery | Agent search observed 2026-11-05; returned names/URLs/descriptions, not settings | Not provided merely by ordinary page search. Needs an explicitly exposed Agent API capability |
| Full current Agent settings | No direct settings reader in the checked connection. Recorded-run readers observed 2026-11-06; configuration can be cut short and published snapshots can predate changes | Not implied by page access. A wrapper exposing the separately permissioned Agent API may differ; unverified here |
| Agent instruction page | Page fetch observed 2026-11-06; fetching `agent://` directly failed in the checked connection | Conditional on page permission, mapping from target to instructions, and complete page/block readers; not live-tested here |
| Native Notion Skill catalog | Enabled-for-external-MCP Skill catalog observed 2026-11-05; not every existing Skill | Page/database enumeration can cover a known management scope, but does not establish native registration, enabled state or a complete catalog |
| Child pages, attachments, reference files, long content | Current suite exercises synthetic retrieval and incomplete-content handling; no new live verification | Needs explicit block/child/file capabilities and completeness/pagination contracts; ordinary search snippets are insufficient |
| Execute-only role | Live run-only access to settings/instructions remains unverified | Discovery, configuration read and instruction read must be checked separately; being able to invoke an Agent elsewhere is not readable instructions |
| Pure comparison/calculation | No universal execution tool is assumed; current fixture verifies a finite Decimal/Fraction substitution | Requires source inspection and equivalence checks for the actual inputs/domain; missing calculation capability is not permission to approximate |
| Write + read-after-write | Not established by the historical read-only runs or this suite | Requires explicitly authorized mutations and complete readback; no live write-compatibility claim here |

The open-source `makenotion/notion-mcp-server` spec was inspected in the earlier record: none of its 17 paths was an Agent path at that time. The separately documented Agent API had additional authentication/permission requirements and was **not run**. Neither historical fact should be generalized to current servers without inspecting their inventory. No new tokens, connections or sharing changes are required merely to read this matrix.

## Historical live observations — not current-source PASS

All rows below come from [Reading Custom Agent instructions and settings](agent-retrieval.md). Date: 2026-11-06. Client/model: Claude Code 2.1.318 / claude-opus-5-5, one Notion workspace, hosted Notion MCP plus Slack connectors. The user could edit two Agents; edit access to the third was unknown. Original runtime revision was not recorded in that document, so it must not be inferred from the current revision that preserves the record.

| Historical case | Observed result | Authorization, limits and reproduction source |
|---|---|---|
| Custom Agent dry run with supplied instruction URL | Instructions and named sources read; dry-run report returned | Read tools allowlisted; write/session tools explicitly unavailable. Five-candidate limit. See Recorded runs in retrieval record; not a write or adversarial-safety test |
| Notion Skill by name | Catalog and page read; review text returned | Same read-only setup, made-up input; no mutations. Replay requires separately authorized live access |
| Agent by name through run history | Own chat and scheduled configuration events read; editable/published pages compared; dry-run report returned | One out-of-allowlist Slack user lookup was refused. No other person's run opened. Same recorded client, role and setup; not recreated here |
| Third Agent, interactive by-name dry run | Published configuration exposed a then-current instruction-rule limitation; user chose to proceed with its page | Partial settings remained unknown; rule was subsequently changed. This is historical diagnostic evidence, not a PASS of the old or current full workflow |

Rebuilding that old environment is not required to replay the synthetic suite. No current live compatibility is claimed for Claude Code, Codex, Pi, editor/run-only roles or an ordinary Notion API wrapper from those records alone.

## Choosing an environment

For discovery, require a real catalog capability or explicitly known management scope. For execution, require readable current adopted instructions, complete necessary resources, allowed tools and task authorization; do not infer these from discovery visibility or edit rights. For dry runs, retain read/coverage limitations and do not mutate messages, completion ledgers or local resume state.

If the native client/model or connection is blocked, resolve that specific prerequisite through the client's configuration/authentication interface and obtain any missing evaluation authorization. Do not substitute another model or a different client and label its result as the blocked cell's PASS. Credentials and business content do not belong in compatibility reports.
