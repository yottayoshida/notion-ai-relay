# Notion AI Relay

Have your AI assistant do the work of a Notion Custom Agent or Notion Skill, from its current instructions.

Notion AI Relay (Relay) is an independent, unofficial Agent Skill that tells your assistant to read those instructions through MCP and do the work itself, instead of starting the Agent or an AI session in Notion. Notion charges a Custom Agent's work to its creator's Select credits, then to the workspace's if an owner allows it; using Notion's API or connected apps without running an Agent uses none ([Notion's pricing](https://www.notion.com/help/custom-agent-pricing)), though your assistant's usage applies. For Custom Agents and Notion Skills alike, Relay also tells your assistant to name the page and version it used, dry-run on request, and ask before writes, messages, other connections, local files or commands you did not name ([execution boundaries](SKILL.md#execution-boundaries)).

## Requirements

- An assistant that loads Agent Skills, such as Claude Code or Codex.
- A [Notion MCP](https://developers.notion.com/docs/get-started-with-mcp) connection, and an MCP server for any other service a workflow uses.
- For Custom Agents: a Notion Business or Enterprise plan; to list Agents or give one by name or URL, Notion AI and Custom Agents access and a connection showing Notion's Agent tools ([tools reference](https://developers.notion.com/guides/mcp/tools-skills-agents-reference)).
- For Notion Skills: access to the Skill's page.
- Your own scheduler for scheduled runs.

What each operation needs: [choosing an environment](docs/compatibility.md#choosing-an-environment).

## Install

Install a release with the [skills CLI](https://github.com/vercel-labs/skills) 1.8.0 or later (Node.js 22.20+):

```bash
npx skills add yottayoshida/notion-ai-relay@v0.1.0
```

Ask Relay for its version, exact for a release-tag install. For newer releases, updates, manual installs and rollback, see [installation maintenance](docs/install-maintenance.md).

## Use

Once Relay is loaded, give the target and this run's input. You need not write in English; see the [response-language rules](SKILL.md#response-language).

For a Custom Agent:

1. Give its name or URL. Relay reads the instructions and settings from Notion's record of a chat you had with the Agent or of its scheduled runs, among its latest 60. If you stop running the Agent in Notion, Relay still uses those records, but they stay as of its last run, instructions too unless your chat recorded the Instructions page ([details](docs/agent-retrieval.md#what-the-run-history-route-assumes)).
2. If Relay asks for it, give the Instructions page URL from the Agent's settings.
3. If that fails too, paste the instructions.

For a Notion Skill, give its name if it is enabled for external MCP clients ("Use in connected agents" in Notion), or its page URL.

```text
List the Notion Custom Agents and Notion Skills I can access.
```

Execution and [dry-run](docs/dry-run-example.md) examples:

```text
Carry out this Custom Agent's task.
Agent: <name or URL>
Input: <target page, time period, and other required input>

Use this Notion Skill to process the supplied material.
Notion Skill: <name or page URL>
Material: <document URL or text>

Dry-run this agent's task without writing to external services.
Agent: <name or URL>
Input: <items to process>
```

## Limits

Relay uses the MCP tools and argument schemas your environment exposes, and needs no Computer Use, browser automation, particular operating system, or client-specific API. When Notion MCP returns a download URL for a file in the same run, Relay downloads it over `https` from a host name, never `localhost` or an IP address, instead of asking you to paste it, in a client that can save it outside your project and Relay's folder, and extract an archive there: from a tar archive of at most 100 members it takes regular files up to 1 MB, and it reports a redirect, other archives (Office files included) and anything beyond these limits. No other URL is downloaded outside MCP, except by a script you approve. Apart from reading its own files and handling these downloads, before the first write, message, non-Notion connection, local file or command you did not name, Relay lists them, with what each write would contain, from what, and any recorded run's date, and waits for your go-ahead. Code from the instructions, their files or the data runs on this machine only if you ask for that script and approve the command you are shown, and then with your access, network included; otherwise its calculation is reproduced by reading it, or reported when it cannot be.

Relay does not launch or drive Notion-side agents or AI sessions: a relayed run happens in your assistant, with its access under your host's permission rules, does not appear in the Agent's Activity, and neither uses nor adds to the Agent's Memories. Whoever can edit the instructions decides what it reads, sends and asks for. A dry run does not update completion state.

This repository distributes instructions, not a production MCP server or background process; fixture servers under `tests/` are for evaluation only. See the dated [compatibility matrix](docs/compatibility.md).

## Docs

[Sample dry run](docs/dry-run-example.md), [troubleshooting](docs/troubleshooting.md), [file guide](docs/files.md).

## License

[MIT](LICENSE).
