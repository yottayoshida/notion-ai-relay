# Resume-handoff cases

These synthetic cases exercise [resumable handoffs](../../references/execute-via-mcp.md#return-a-resumable-handoff), not live Notion compatibility. The fixture does not contain business data, credentials, or a real connection. Its tool names describe capabilities, not a required MCP schema.

## Replay protocol

1. Freeze `SKILL.md` and all three runtime references, `cases.json`, `mock_mcp.py`, and `score.py`, with the shared `tests/_mcp_fixture.py` and `tests/_support.py`. Record file digests, revision, client/adapter, date, model and thinking setting, case/time/turn limits before model execution. Obtain authorization for model use; do not auto-retry a failed run or silently change model.
2. Start one fresh conversation per case with the current model/thinking setting. Expose only a read tool limited to the frozen Skill/references and the one tool of a separate fixture process per case. No shell, file writing, real MCP, discovered extensions, other agents, or previous conversations are needed.
3. Instruct the assistant to load the local Skill and relevant references, then give it only the case's `request`, not `expected`, other cases, the mock implementation, or scoring criteria. The fixture is a newline-delimited JSON-RPC stdio MCP server, like the other suites' fixtures: `python3 tests/resume-handoff/mock_mcp.py --case <case-id> --trace <trace.jsonl>`. Its one tool, `mock_mcp`, takes `operation`, one of `OPERATIONS` in `mock_mcp.py`, and, for `read_item`, `read_result`, `create_result` and `advance_checkpoint`, an `item` that is A, B or C. Omit `item` for the other operations; `null` is refused like any other value outside A to C. The fixture records even prohibited effects rather than hiding them behind host-side success guards; a call it refuses for its arguments is recorded as well and fails the operation checks, as in the other suites.
4. Preserve the visible model/tool trace, final response, the fixture's trace, read coverage, usage, errors, exit status, and any timeout. The trace starts with a line naming the case and server; each later line is one call with its tool name, arguments and result, as in the other suites, plus the items verified before it and the checkpoint after it. The model sees only each tool result, not the trace or expected values.
5. Run deterministic checks with `python3 -B tests/resume-handoff/score.py <case-id> <trace.jsonl> <final.txt>`, adding `--incomplete` for a timeout, missing required loading, or unsettled run. The scorer reads the trace and final message as UTF-8 and rejects a trace without its start line. Exit 0 means operation checks passed, **not** that all handoff requirements passed. A human must inspect every listed `human_review_required` fact and each case's `prohibited` list against the final response and trace. Accept equivalent language/formatting. Missing facts, invented IDs/records, adopted ambiguous state, or plans reported as real completion fail the case. Record human judgments separately; do not tune expectations after seeing a response.

A complete case PASS requires the operation checks, human semantic checks where applicable, full relevant Skill reads, normal settling, and no mandatory skips/timeouts. No case needs a new persistent run record. `normal-resume-output-only` is the normal-path control: no native run ID exists, B's prior creation is found, only C is created and read back, the existing checkpoint advances only for verified work, and the result remains the exact requested JSON object without a handoff wrapper.

## Cheap fixture/scorer controls

From the repository root:

```bash
python3 -B -m unittest discover -s tests -p test_resume_handoff_fixture.py -v
```

Controls cover a valid resume, effects before current configuration retrieval, invalid retry, advancing an unverified checkpoint, an external read after stop, ambiguous run effects, dry-run write/rollback/record attempts, input access denial, and output-only preservation. `score.py` also requires a `read_item` attempt for every item listed in a case's `items_read`, counting attempts that return an error: in `partial-dry-run`, a handoff that reports C as held for missing input access fails unless C's input was actually requested. They test the fixture and scorer, **not** model behavior. Textual handoff quality is deliberately not reduced to required-word matching.

## Limits

`stopped-partial` supplies the execution context at the moment of stop; it does not test client interrupt delivery or reconstruct a whole earlier conversation. Configuration-source session privacy, live history-reader schemas, client Skill discovery, and real Notion writes/read-back are outside this fixture. The access-denial case tests the distinction between a dry-run plan and the prior verified execution checkpoint, without persistence. Passing these four one-shot cases is not a reliability guarantee or a comparison with the prior Skill.
