# Response-language checks

## Scope

The primary implementer manually traced the cases below against the [response-language rules](../SKILL.md#response-language). Each row records the result of that instruction walkthrough, not observed client or model behavior. No additional model, Codex session, or Notion MCP run was launched. These checks do not establish runtime language compliance or client compatibility.

The fixtures are synthetic. The repository-owned runtime instructions (`SKILL.md`, `references/`, and `agents/openai.yaml`) remain in English; retrieved third-party instructions and user material need not be translated.

## Instruction walkthroughs

| Case | Request and context | Result of applying the rules |
|---|---|---|
| Japanese request, English Skill | `この手順を実行して、結果を報告してください。` No required deliverable language. | Progress, questions, errors, and the final report use Japanese. The Skill's English text does not determine response language. |
| Explicit override | `この手順を実行してください。Reply in English.` | User-facing responses use English because the explicit choice precedes the request's language. |
| JSON-only output | `結果をJSONだけで返してください。` Schema: `{"status": "enum: ok or error", "summary": "string"}`. | Keep the keys and enum values unchanged, use Japanese for a translatable summary, and add no surrounding explanation; e.g. `{"status":"ok","summary":"対象なし"}` for a fixture with no targets. |
| Delegated instructions differ | Japanese request; parent instructions in English; delegated Skill instructions and an example report in French, with no required French deliverable. | User-facing responses and translatable report prose use Japanese, not the delegated example's French. |
| Required deliverable language | Japanese request to draft an English email, without sending it. | The draft remains English. Any permitted progress or explanation is Japanese. If only the draft is required, return the English draft alone. No send is added. |
| Ambiguous mixed input | `Run / 実行` after a clearly Japanese conversation. | Use Japanese from the established conversation; do not ask unnecessarily. If no language is established and the ambiguity matters, ask only for the needed language choice. |
| Protected content | Japanese request; output includes key `page_id`, ID `abc123`, code `return 1`, and a quotation required verbatim: `Keep this text.` | Preserve these items, the schema, and required formatting while translating only eligible natural-language content. |
| Error or missing input | Japanese request, but a required page cannot be read or the execution target is ambiguous. | Report the error or request the missing selection in Japanese; retrieved error text does not change the response language. |

All eight cases have a defined outcome under the revised instructions. This is a self-review of the specification, not an independent review or an executed behavioral evaluation.

## Reproducible static checks

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
```

`tests/test_response_language.py` checks the presence of the language-precedence, message-scope, format-preservation, and deliverable-language contracts. It does not implement a language classifier or pretend to execute the Skill. Before the new section was added, all three tests failed (seven failed assertions, including subtests); with it, all three pass, with no skips. Diff whitespace checks also pass.

Actual client behavior for these cases remains unverified. A future behavioral evaluation must record the client, model, Relay revision, inputs, outputs, and tool trace separately rather than reusing these static results.
