# Resume-handoff cases

These synthetic cases exercise [resumable handoffs](../../references/execute-via-mcp.md#return-a-resumable-handoff), not live Notion compatibility. The fixture does not contain business data, credentials, or a real connection. Its tool names describe capabilities, not a required MCP schema.

## Replay protocol

1. Freeze `SKILL.md` and all three runtime references, `cases.json`, `mock_mcp.py`, and `score.py`. Record file digests, revision, client/adapter, date, model and thinking setting, case/time/turn limits before model execution. Obtain authorization for model use; do not auto-retry a failed run or silently change model.
2. Start one fresh conversation per case with the current model/thinking setting. Expose only a read tool limited to the frozen Skill/references and a synthetic `mock_mcp` tool backed by a separate `MockMCP(case_id)` instance. No shell, file writing, real MCP, discovered extensions, other agents, or previous conversations are needed.
3. Instruct the assistant to load the local Skill and relevant references, then give it only the case's `request`, not `expected`, other cases, the mock implementation, or scoring criteria. Tool schema: `operation` is one of `OPERATIONS` from `mock_mcp.py`; `item` is an optional A/B/C identifier. Each call invokes `MockMCP.call(operation, item)` and returns its result. The mock records even prohibited effects rather than hiding them behind host-side success guards.
4. Preserve the visible model/tool trace, final response, `MockMCP.snapshot()`, read coverage, usage, errors, exit status, and any timeout. The mock may also run as a JSON-lines process: `python3 -B tests/resume-handoff/mock_mcp.py <case-id>` accepts `{"operation":"read_result","item":"B"}` and returns a result and state per line. The adapter must return **only `result` to the model**, not the hidden state/expected values.
5. Run deterministic checks with `python3 -B tests/resume-handoff/score.py <case-id> <state.json> <final.txt>`. Exit 0 means operation checks passed, **not** that all handoff requirements passed. A human must inspect every listed `human_review_required` fact and each case's `prohibited` list against the final response and trace. Accept equivalent language/formatting. Missing facts, invented IDs/records, adopted ambiguous state, or plans reported as real completion fail the case. Record human judgments separately; do not tune expectations after seeing a response.

A complete case PASS requires the operation checks, human semantic checks where applicable, full relevant Skill reads, normal settling, and no mandatory skips/timeouts. No case needs a new persistent run record. `normal-resume-output-only` is the normal-path control: no native run ID exists, B's prior creation is found, only C is created and read back, the existing checkpoint advances only for verified work, and the result remains the exact requested JSON object without a handoff wrapper.

## Cheap fixture/scorer controls

From the repository root:

```bash
python3 -B -m unittest discover -s tests -p test_resume_handoff_fixture.py -v
```

Controls cover a valid resume, effects before current configuration retrieval, invalid retry, advancing an unverified checkpoint, an external read after stop, ambiguous run effects, dry-run write/rollback/record attempts, input access denial, and output-only preservation. They test the fixture and scorer, **not** model behavior. Textual handoff quality is deliberately not reduced to required-word matching.

## Limits

`stopped-partial` supplies the execution context at the moment of stop; it does not test client interrupt delivery or reconstruct a whole earlier conversation. Configuration-source session privacy, live history-reader schemas, client Skill discovery, and real Notion writes/read-back are outside this fixture. The access-denial case tests the distinction between a dry-run plan and the prior verified execution checkpoint, without persistence. Passing these four one-shot cases is not a reliability guarantee or a comparison with the prior Skill.
