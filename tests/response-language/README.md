# Response-language cases

`cases.json` checks the [response-language rules](../../SKILL.md#response-language): replies and returned results use the user's requested language, or else the request's language, unless the procedure or the user requires another language for a result; machine-facing formats stay intact; and content written to a destination keeps the stated language, or else the Agent's own. These are model decision cases with synthetic snapshots, not tests of client loading or real MCP calls.

## Replay

1. Give the model `SKILL.md` and every file in `references/` as loaded instructions, in a fresh conversation for each case.
2. Send the case's `prompt` as the user's message. Do not supply `expected`.
3. Check the reply against `expected`: the language of the user-facing text, the computed total where given, the output format, anything listed under `must_not`, and, for the destination and returned-draft cases, the language of the post or draft separately from the reply. JSON output must parse and keep the requested keys and values; the language of text inside it is not checked, because the rules leave machine-readable output out of scope. A missing or malformed result is a failure.

Keep raw runs outside the repository and report the model, settings, and results with the change.
