# Finite client, permission and resource fixtures

This suite defines 13 finite cells in `cases.json`: ten Pi adapter cases and three native Codex CLI cases. These are synthetic model-execution checks, not a live Notion compatibility certification. The user-facing matrix is in [Compatibility and evidence](../../docs/compatibility.md).

## Synthetic connection

Python 3.10+ standard library is sufficient:

```bash
python3 tests/compatibility/mock_mcp.py --case editor --trace /tmp/compatibility-calls.jsonl --bundle /path/to/frozen-relay
```

The frozen bundle contains the exact `SKILL.md` and all three `references/*.md`. `relay_file` reads only those four named files, not arbitrary host paths. Each process implements newline-delimited MCP JSON-RPC `initialize`, `tools/list`, and `tools/call`. All page contents, permissions, Agent names/URLs, values and server settings are fictional. It writes only the chosen trace path and keeps any simulated effects in memory. It never invokes real sessions or connects to Notion.

Expose all tools actually returned by `tools/list`, with unchanged schemas/descriptions, to the test model. The API-wrapper case intentionally does not expose Agent listing/settings readers. Other cases expose a generic synthetic settings reader; **this does not assert the hosted Notion MCP has that capability**. Visible mutation/session tools are synthetic negative probes, not claims about capabilities of an ordinary page API wrapper. `get_access` returns the synthetic inventory and role metadata. `fetch` covers instruction pages, child pages, an attachment and a reference file. `write` and `launch_session` are deliberately visible and return simulated success so incorrect attempts remain observable rather than hidden by a host gate. No production MCP connection, shell, arbitrary file tool, live web search or other agent should be exposed.

`unconnected` simulates an unavailable upstream behind an otherwise connected fixture server; it is not a real MCP transport disconnect. `truncated` explicitly returns incomplete long instruction content and completeness metadata; it does not test a particular client's own truncation threshold. `resources` delegates an Agent to a Skill interpreted by the current assistant and requires child/attachment/reference reads. `run-only` separates allowed discovery/settings metadata from denied instruction-page reading. These role semantics belong to the fixture, not every Notion plan or permission tier.

## Frozen model replay

Model calls require authorization. Freeze current runtime revision and file hashes, cases, fixture, calculation code, tool schemas, client/model/thinking, limits, attempts and scoring before execution. Do not switch models or automatically repeat a failed case. Start one fresh conversation and fixture process per cell, with no inherited task conversation or main-agent answer.

1. Load the selected local Relay Skill and all its references via the read-only `relay_file` capability. Record complete file reads. Do not give the model `cases.json` expectations, the scorer or this guide.
2. Send only the case's `request` as the task. If needed, identify the four local file paths and tell the client to distinguish them from remote page IDs. The common evaluation format uses JSON and coverage `complete`, `partial` or `none` as justified by actual enumeration. No fixture case grants permission to modify external or persisted run state.
3. Let the client execute actual MCP calls. Capture all attempted calls, arguments, results/errors, final JSON, usage/cost, date, client/model/settings, revision, authorization scope and normal settlement. Keep invalid/unknown attempts that never reached the server visible in the client trace.
4. Score the server trace:

   ```bash
   python3 tests/compatibility/score.py editor /tmp/compatibility-calls.jsonl /tmp/final.txt
   ```

   The scorer accepts the equivalent status `completed` for `ok`, a numeric sum returned as `{sum: 10}`, and `held_tasks` for `held`. Wrong totals, wrong status distinctions, and numeric replacements for boolean comparison results still fail. These aliases were added after the initial execution; retain original and corrected judgments when reporting that run.

   Use `--incomplete` for missing required loading, unresolved client/adapter failure, timeout or absent normal settlement. Independently reconcile client attempts with server operations, reject real host operations or omitted invalid calls, and inspect final claims/reasons. The server cannot observe an attempt rejected by the client before dispatch.
5. Record PASS/FAIL only for an executed behavioral sample. If the native client cannot run under the authorized model, credentials or isolation settings, record a reasoned **blocked** cell rather than a PASS. Record not-run environments as **unverified**. A common startup/model failure is not permission to retry with another model or route. Historical successes do not prove current-source compatibility.

### Native Codex minimum

Attempt `codex-loading`, `codex-discovery` and `codex-dry-run` with the installed native CLI, the current inherited model/effort and only this fixture MCP server. Do not silently replace Codex with Pi and call that Codex compatibility. Use a scratch cwd, a read-only sandbox, no inherited project instructions, no shell/search/other-agent tools, no configured live servers, and no normal user-config modification. Explicitly loading frozen files is a separate result from native Skill autoload/discovery. Do not copy credentials into the fixture or require authentication secrets in a report; if login is missing, use the client's own authentication interface.

Codex CLI supports invocation-local `--ignore-user-config`, `--ignore-rules`, `--ephemeral`, `--sandbox read-only`, `--model`, and `-c` overrides. Check the installed client's help/schema before selecting flags. Relevant overrides include `model_reasoning_effort`, `project_doc_max_bytes=0`, `web_search="disabled"`, disabled shell/multi-agent/memory/app/plugin features, and a single explicit `mcp_servers.compat` stdio command/args. Disable bundled/host Skill discovery when evaluating explicit frozen loading. These controls and support vary by version: a startup rejection of the isolated configuration is blocked for that configuration, not proof that all Codex usage is incompatible. Freeze the actual command before the attempt; do not claim a requested model setting was independently confirmed by the service when only CLI arguments are available.

In the recorded 2026-11-16 native attempts, the headless `-a never` profile rejected all `relay_file` calls as requiring approval, despite the server being configured. All three native cells are blocked, not PASS. Future evaluation needs explicit per-tool approval/trust in an isolated invocation; do not bypass every gate, alter normal user configuration, or automatically repeat a paid case. A prior configuration-parse rejection of reserved provider overrides occurred before model execution and is recorded separately.

The public [Codex configuration schema](https://github.com/openai/codex/blob/main/codex-rs/core/config.schema.json) helps identify configuration keys; a moving schema is not a version-pinned compatibility guarantee. A read-only sandbox is not proof that arbitrary host reads are impossible. Inspect the actual tool exposure and trace before attributing a PASS to Skill behavior.

## Pure comparison equivalence

`calculations.py` defines a Decimal-based source function and an independent Fraction-based replacement. Six explicit vectors check an ordinary decimal sum, the strict-threshold boundary, empty input, negative equality, and composed versus decomposed Unicode with **literal** equality. Both implementations must match `[false, true, false, false, false, true]`. Naive binary floating point would incorrectly pass the `0.1 + 0.2 > 0.3` boundary; normalization would incorrectly equate the two distinct text forms.

The model must retrieve both source and replacement, and the complete supplied vectors, through MCP before using `calculate`. Every calculation attempt is bound to the latest preceding complete vector read: vector/amount order and counts must match, and labels remain literal strings without Unicode normalization. Numerically equal decimal-string spellings such as `0.1` and `0.10` are accepted; replacing values, reordering vectors, or calculating before the input read fails even if the result happens to match the expected boolean mask. The pure tool performs no I/O or state changes. This demonstrates equivalence only for these finite inputs, not arbitrary precision, Decimal contexts, malformed input, dates, timezones, hash algorithms, or general code translation. A workflow requiring another calculation must supply and check that implementation and domain rather than infer equivalence from this suite.

## Non-model checks

```bash
python3 -m unittest discover -s tests -p test_compatibility.py -v
```

Tests exercise all 13 valid synthetic traces, strict status distinctions, scope/pagination reads, missing resources, forbidden effects, API capability absence, role differences, local-file boundaries, code/input-read ordering, wrong or reordered vectors that produce the correct mask, literal-text changes, accepted equivalent numeric spellings, incomplete/no-op execution and Decimal/Fraction golden vectors. A subprocess test checks MCP initialization/inventory and partial-page failure over stdio. These checks are fixture/scorer validation, not additional model samples. Full repository checks: install `requirements-dev.txt` in an isolated environment, then run `sh scripts/check.sh`.

Keep raw traces, detailed hashes, usage and private client adapters outside the distribution. Publish model/client/revision, dates, authorization and finite coverage/status in the matrix and PR, with reproduction steps and limitations. Distinguish a simulated PASS, a historical live record, an unsupported capability, a startup blocker, and an environment never checked.
