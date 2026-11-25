# Security policy

Notion AI Relay is a set of instructions that an AI assistant reads. Its boundaries are text the model is asked to follow; the host's permissions are what finally stop an action. Report problems in either of the areas below privately, not in a public issue.

## In scope

- **Getting around the runtime boundaries.** A reproducible input, such as the text of a Notion page, a Skill's instructions, or a recorded run, that makes a model reading the [execution boundaries](SKILL.md#execution-boundaries) as written cross them, or a place where that text itself permits crossing them.
- **Evaluation code that reaches the machine running it.** A defect in `tests/` or `scripts/` that reads, writes, or fetches outside what it states, for example a fixture file reader that returns files other than the frozen Relay files, a download fixture that contacts a real host, or the installation replay writing outside its temporary root. A fixture or scorer that reports PASS while hiding a way around the boundaries also belongs here.

## Out of scope

- A jailbreak that works the same without Relay, and anything the host's own permissions allow. Report those to the client or model provider.
- Vulnerabilities in Notion, an MCP client, or a model. Report those to their providers.
- Other wrong results from a fixture or scorer, and mistakes in the documentation. Open a public issue.

## How to report

Use [private vulnerability reporting](https://github.com/yottayoshida/notion-ai-relay/security/advisories/new). Include a reproduction rebuilt from synthetic data, the client and model, the Relay commit, and what happened. Do not include what [installation maintenance](docs/install-maintenance.md#5-confirm-reload-and-diagnose-without-secrets) says not to send: tokens, credential stores, business page contents, or complete conversation logs.

This project is maintained by one person. There is no response deadline; reports are answered as time allows. Fixes land on `main`; there are no separately maintained releases.
