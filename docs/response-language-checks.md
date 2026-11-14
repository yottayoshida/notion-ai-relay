# Response-language checks

## Scope

The primary implementer first manually traced the cases below against the [response-language rules](../SKILL.md#response-language). Those walkthroughs are not model executions. A subsequent, explicitly authorized evaluation executed four cases once each with a real model through Pi CLI; its results are recorded separately below. Neither check establishes general client compatibility.

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

## Executed model checks

On 2026-11-14, the four [synthetic fixtures](../tests/fixtures/response-language.json) were each executed once in fresh Pi CLI 1.5.2 processes, inheriting the parent session's provider (`openai-codex`), model (`gpt-6.1-sol`), and thinking level (`xhigh`). The fixtures and expected language, format, and total were written before execution. No implementation or design work was delegated.

| Fixture | Observed final output | Verdict |
|---|---|---|
| Japanese request, English Skill | `合計は10です。` | PASS |
| Explicit English override | `The total is 10.` | PASS |
| JSON-only output | `{"status":"ok","source_id":"fixture-03","total":10,"summary":"合計は10です。"}` | PASS |
| English Agent, French delegated Skill | `合計は10です。` | PASS |

The primary implementer inspected the actual language and meaning; JSON parsing checked the keys, enum, ID, and total. All four processes exited 0, settled without abort, and produced one completed assistant message each. There were zero skips, timeouts, tool calls, retries, or compactions. The [execution record](response-language-results.json) includes exact outputs, timestamps, runtime revision and digest, fixture digest, token usage, and raw-trace digests. The catalog-based cost estimate is USD 0.04783, not a provider billing receipt.

Raw JSONL event traces and the local runner remain outside the distribution in workspace `artifacts/notion-ai-relay-14-behavior/`. Only final outputs and execution metadata are included here, not reasoning traces or local configuration paths.

### Reproduction setup

Each process used an isolated working directory with this process-local `.pi/settings.json`:

```json
{"retry":{"enabled":false,"provider":{"maxRetries":0}},"compaction":{"enabled":false}}
```

`runtime.md` concatenated the recorded revision's `SKILL.md`, `references/read-configuration.md`, `references/read-skills.md`, and `references/execute-via-mcp.md` in that order, separated by two newlines and with `<!-- relative/path -->` followed by a newline before each file. The full instructions, not just the language section, were appended to Pi's default system prompt. For each fixture, `prompt.txt` contained its exact `prompt` value. The invocation was:

```bash
pi --mode json --no-session --offline \
  --no-extensions --no-mcp --no-tools --no-skills \
  --no-prompt-templates --no-themes --no-context-files --approve \
  --provider "$PI_PROVIDER" --model "$PI_MODEL" --thinking "$PI_REASONING_LEVEL" \
  --append-system-prompt runtime.md < prompt.txt > events.jsonl 2> stderr.log
```

The model options were frozen from the parent session before starting, not selected per result; normal Pi settings and credential stores were not edited. Reproduction makes four new model invocations and needs its own authorization. The local runner imposed a 240-second limit per case and did not retry failed cases.

### Remaining limits

This is a four-sample, single-model instruction-following check using supplied snapshots. It does not test Notion MCP retrieval, Codex CLI Skill loading, delegated tool calls, or the other four walkthrough scenarios. Tools and MCP were disabled, so zero calls are not evidence of the model refusing unsafe operations. There was no pre-change model run: the results do not prove that the new section caused an improvement. They are not an independent review or a guarantee of consistent future behavior.
