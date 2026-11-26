# Notion AI Relay

Have your AI assistant do the work of a Notion Custom Agent or Notion Skill, from its current instructions.

Notion AI Relay (Relay) is an independent, unofficial Agent Skill that tells your assistant to read those instructions through MCP and do the work itself, instead of starting the Agent or an AI session in Notion. Notion charges a Custom Agent's work to its creator's Select credits, then to the workspace's if an owner allows it; using Notion's API or connected apps without running an Agent uses none ([Notion's pricing](https://www.notion.com/help/custom-agent-pricing)), though your assistant's usage applies. For Custom Agents and Notion Skills alike, Relay also tells your assistant to name the page and version it used, dry-run on request, and ask before writes, messages, other connections, local files or commands you did not name ([execution boundaries](SKILL.md#execution-boundaries)).

## Requirements

- An assistant that loads Agent Skills, such as Claude Code or Codex.
- A [Notion MCP](https://developers.notion.com/docs/get-started-with-mcp) connection, and an MCP server for any other service a workflow uses.
- For Custom Agents: a Notion Business or Enterprise plan; to list Agents or give one by name or URL, Notion AI and Custom Agents access and a connection showing Notion's Agent tools ([tools reference](https://developers.notion.com/guides/mcp/tools-skills-agents-reference)).
- For Notion Skills: access to the Skill's page.
- Your own scheduler for [scheduled runs](docs/scheduling.md).

What each operation needs: [choosing an environment](docs/compatibility.md#choosing-an-environment).

## Install

Install a release with the [skills CLI](https://github.com/vercel-labs/skills) 1.8.0 or later (Node.js 22.20+):

```bash
npx skills add yottayoshida/notion-ai-relay@v0.1.0
```

Ask Relay for its version, exact for a release-tag install. For newer releases, updates, manual installs and rollback, see [installation maintenance](docs/install-maintenance.md).

## Use

Once Relay is loaded, give the target and this run's input. You need not write in English ([response-language rules](SKILL.md#response-language)).

For a Custom Agent:

1. Give its name or URL. Relay has your assistant read the instructions and settings from Notion's record of a chat you had with the Agent or of its scheduled runs, among its latest 60. If you stop running the Agent in Notion, those records still serve, but they stay as of its last run, instructions too unless your chat recorded the Instructions page ([details](docs/agent-retrieval.md#what-the-run-history-route-assumes)).
2. If Relay asks for it, give the Instructions page URL from the Agent's settings.
3. If that fails too, paste the instructions.

For a Notion Skill, give its name if it is enabled for external MCP clients ("Use in connected agents" in Notion), or its page URL.

```text
List the Notion Custom Agents and Notion Skills I can access.
```

Try a [dry run](docs/dry-run-example.md) first:

```text
Dry-run this agent's task without writing to external services.
Agent: <name or URL>
Input: <items to process>

Carry out this Custom Agent's task.
Agent: <name or URL>
Input: <target page, time period, and other required input>

Use this Notion Skill to process the supplied material.
Notion Skill: <name or page URL>
Material: <document URL or text>
```

## Limits

Relay tells your assistant to:

- list each write, message, non-Notion connection, local file or command you did not name (besides reading its files and Notion downloads), with what each write would contain and from what, and wait for your go-ahead;
- run code from the instructions or their files only if you ask for that script and approve its command;
- download only files Notion MCP returns ([rules](docs/permissions.md));
- start, message, wait on or stop no Notion AI session, and leave the Agent's schedule and triggers alone unless you ask;
- leave completion state alone in a dry run.

These are instructions the model is asked to follow. Only your client's permission settings stop a call, and they act per tool or command, not per rule above. For Claude Code, add these to `permissions.deny` in your project's `.claude/settings.json` to deny Notion's session-control tools:

```json
{"permissions": {"deny": ["mcp__*__notion-spawn-session", "mcp__*__notion-send-message-to-session", "mcp__*__notion-stop-session", "mcp__*__notion-wait-session", "mcp__*__notion-search-sessions"]}}
```

In a local `claude -p` test (2.1.331, 2026-11-25) it stopped those calls in the default, `dontAsk`, `acceptEdits` and `auto` modes; bypass mode was not tested. Approve writes, messages and commands one at a time, and for a dry run deny the write tools ([dry runs](docs/permissions.md#dry-runs)).

Writes use each connection's account and access; Notion's MCP tools "act with your full Notion permissions" ([Notion's help](https://www.notion.com/help/notion-mcp)). The Agent keeps its own schedule, so it and a relayed run can act on the same day; pause it if that matters. A relayed run takes place in your assistant: it does not appear in the Agent's Activity and, by Notion's description, neither uses nor adds to the Agent's Memories (inferred, not observed). Whoever can edit the instructions decides what Relay reads, sends and asks for.

This repository distributes instructions, not a production MCP server or background process; fixture servers under `tests/` are for evaluation only ([compatibility matrix](docs/compatibility.md)).

## Docs

[Sample dry run](docs/dry-run-example.md), [troubleshooting](docs/troubleshooting.md), [file guide](docs/files.md).

## License

[MIT](LICENSE).
