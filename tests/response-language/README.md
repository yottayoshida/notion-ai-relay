# Response-language cases and scoring

`cases.json` contains seven synthetic supplied-snapshot cases for the [response-language rules](../../SKILL.md#response-language). Replies and returned results use the requested response language unless a deliverable requires another language. Destination content is judged separately. Machine-facing formats remain intact; the language of text inside JSON is outside the current rule. These cases do not test client autoload, real MCP calls or actual posting. The two destination cases name `#team-updates` in the request, so a post they describe needs no go-ahead under the [execution boundaries](../../SKILL.md#execution-boundaries); runs recorded before that wording said only that posting to Slack was approved.

## Frozen replay

1. Before any model use, obtain authorization and freeze `SKILL.md`, all `references/`, `cases.json`, this scorer, runtime/input digests, model/thinking, attempt/time/turn limits and scoring criteria. Use a fresh conversation for each case; record how the Skill was loaded. Client autoload and supplied loaded text are different evidence.
2. Give the assistant the loaded runtime instructions and only the case's `request`, not `expected`, this guide, the scorer or semantic judgments. Preserve the exact request and its output-only/block requirements. Do not provide real service tools for these supplied-snapshot cases.
3. Preserve exact output, revision/digests, client/model/thinking, settlement, limits, errors and usage. Do not automatically retry failures, switch models, or rewrite expectations after observing output. A missing run, timeout or missing Skill load is incomplete.
4. Run the scorer against the saved UTF-8 output and an independently recorded semantic assessment as below. Keep raw logs, hashes and usage outside the distribution; report scope/results/limits with the change.

## What the scorer can and cannot determine

`score.py` checks JSON syntax, exact keys/enum/ID/total, a nonempty text summary, and the POST/REPLY or DRAFT/optional NOTE block structure. It accepts Markdown headings, bold labels, colons and CRLF as alternative block formatting. A label on a plain line must be upper case (`POST`, not `Post:`), so that a line such as `Note:` inside a draft stays part of it. POST/REPLY output may have a preamble; that prose is judged separately in the reply language. Duplicate/empty/missing blocks, extra JSON commentary, and preambles outside the DRAFT/optional NOTE format are rejected.

It is **not a language classifier** and does not infer meaning from a required word, script character, or digit. A human must inspect the actual output, then record its observed segment languages, correct meaning, and requested format. Do not copy `expected` into the judgment or accept the assistant's self-reported language as evidence. Manual grading is not independent review unless a separate reviewer actually performed it.

- Plain replies: verify the single-sentence format, correct total (10, including words such as “ten” or “十”), and language. A French delegated example does not require a French reply or its example total 6.
- POST and REPLY: judge each separately. A Japanese reply does not make a Japanese post correct when the task/Agent requires English. A preamble, if present, also needs its own `preamble` language judgment matching the reply language; a correctly localized REPLY does not excuse a wrong-language introduction. Check the actual proposed task summary as well as the language.
- DRAFT and NOTE: the draft must preserve the required English vendor/date content. Any note must be Japanese; omitting an optional note is valid. Do not add a send.
- JSON: preserve keys, `ok`, `fixture-03`, a total that is exactly 10 as a JSON number (`10`, `10.0` and `1e1` are the same value; `10.0000000000000001` is not) and a truthful natural-language summary. The summary's language is unrestricted, not silently required to be Japanese.

Assessments bind to the exact output with `output_sha256` (SHA-256 of the UTF-8 bytes, including whitespace). The scorer refuses a stale assessment. For example, a manually inspected English post with Japanese reply uses:

```json
{
  "output_sha256": "<digest-of-this-output>",
  "format_ok": true,
  "meaning_ok": true,
  "languages": {"post": "English", "reply": "Japanese"}
}
```

Plain numeric-reply cases also require `"total": 10`. Use `reply`, `post`, `draft`, `note` and optional post-preview `preamble` roles as applicable; JSON has no required language judgment. Judge the translatable prose, not protected IDs, names, code, or quotations. Record observed values even when wrong: `"post": "Japanese"` must fail an English-post case, rather than being relabeled to match its expectation.

```bash
# Without an assessment: show structural results/digest, but exit 1 (not a case PASS).
python3 tests/response-language/score.py destination-language-unstated output.txt
# After semantic inspection:
python3 tests/response-language/score.py destination-language-unstated output.txt --assessment judgment.json
```

Use `--incomplete` for an unsettled/failed run. Exit 0 requires both structural checks and the output-bound semantic judgment. This verifies consistency of the recorded judgment with the fixture; it cannot prove that a human labeled the language or meaning correctly.

## Offline scorer controls

```bash
python3 -B -m unittest discover -s tests -p test_response_language_scoring.py -v
```

Controls cover all seven valid examples and alternative wording/formatting, valid and wrong-language preambles, unchanged JSON/draft-only restrictions, wrong French delegation, separately wrong post/reply languages, required English drafts, optional notes, JSON corruption/keys/enum/ID/total, stale/missing judgments, wrong totals and incomplete runs. These are tests of the scorer, **not executions of the revised Skill**. No sentence-presence assertions against `SKILL.md`, additional dependencies, model calls, or network access are required.

The wording candidate and these controls do not establish a behavioral improvement or resolve the previously recorded Claude inconsistency. Keep the PR held until the separately authorized behavioral checks and review are assessed; do not reuse historical passes for changed instructions.
