# Discovery and execution cases

`cases.json` holds two model decision cases with synthetic results: a list request returns the list and runs nothing, even after a target was chosen earlier in the conversation, and an explicit request to carry out a task is still treated as execution. No code scores them. They are not tests of Codex loading the Skill or of real MCP calls. The default prompt in `agents/openai.yaml` is pinned by `tests/test_structure.py`.

## Replay

1. Give the model `SKILL.md` and every file in `references/` as loaded instructions, in a fresh conversation for each case.
2. Supply the case's `conversation` as the earlier turns, `request` as the new message, and `discovery_results` as what the listing tools returned. Do not supply `expected`.
3. Ask for one JSON object: `action`, `target` (null unless executing), `writes` (external writes planned for this message), and a short reason. `action` is `list` for returning the list, `execute` for starting the task's procedure, including waiting for a go-ahead before the first write, and `ask` only when the target or input is missing or ambiguous.
4. Compare `action` with `expected`, and `target` by name or by the URL listed in `discovery_results`. For `list-after-selection`, `writes` must also be empty. A prose-only answer, malformed JSON, or a missing result is a failure.

Model calls need the operator's authorization. Keep raw runs outside the repository and report the model, settings, and results with the change.
