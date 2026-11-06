# Notion AI Relay

Run Notion agents and skills through MCP.

Notion AI Relay is an Agent Skill that reads the instructions of a Notion Custom Agent or Notion Skill and lets your current AI assistant carry out the work through MCP. It reads each target at runtime instead of storing its workflow in this repository.

## Install

Install with the [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add yottayoshida/notion-ai-relay
```

For manual installation, put this repository in your client's Skill directory as a folder named `notion-ai-relay`, the `name` in `SKILL.md`, for example with `git clone https://github.com/yottayoshida/notion-ai-relay.git`. A GitHub zip extracts to `notion-ai-relay-main`; rename it, because a client may name the Skill after its folder. Keep `SKILL.md` and `references/` together. `agents/openai.yaml` contains optional Codex display metadata.

Connect Notion MCP in your AI assistant separately. If a workflow uses another service, connect an MCP server that supports the required operations for that service.

## Use

After your assistant loads the Skill, specify the target and the input for this run.

For a Custom Agent, also supply its instructions. If they live on the Agent's Instructions page, give that page's URL (copy the link from the Agent's settings): the Skill reads the page through MCP on every run, so it follows the instructions the Agent currently runs rather than a copy. Otherwise paste the instruction text. The hosted Notion MCP cannot read an Agent's settings from its `agent://` URL; [Agent retrieval](docs/agent-retrieval.md) compares the routes.

```text
List the Notion Custom Agents and Notion Skills I can access.

Carry out this Custom Agent's task.
Agent URL: <target agent URL>
Instructions: <Instructions page URL, or pasted text>
Input: <target page, time period, and other required input>

Use this Notion Skill to process the supplied material.
Skill URL: <instruction page URL>
Material: <document URL or text>

Dry-run this agent's task without writing to external services.
Agent URL: <target agent URL>
Instructions: <Instructions page URL, or pasted text>
Input: <items to process>
```

## Requirements and limits

The Skill maps each operation to the MCP tools and argument schemas exposed by your environment. It does not require Computer Use, browser automation, a particular operating system, or a client-specific automation API.

| Operation | Required information or capability |
|---|---|
| List Custom Agents | An MCP agent-listing capability. Results cover the scope exposed by the connection |
| List Notion Skills | An MCP Skill-listing capability, or a known Skill page or database. The hosted Notion MCP lists only Skills enabled for external MCP clients |
| Carry out a Custom Agent's task | Its instructions, a verified or user-supplied link to the target, required settings and input, and the necessary MCP operations |
| Carry out a Notion Skill's task | Its instruction page, required references and attachments, current input, and the necessary MCP operations |
| Run on a schedule | A separately configured scheduler or event receiver |

Some MCP connections cannot retrieve full Agent settings. In those cases, provide an instruction-page URL, the instruction text, or the missing settings. Pasted text, and pages other than the Agent's own Instructions page, are not treated as a verified current published version. Missing registration or enabled-state metadata does not prevent execution of an explicitly selected procedure when its instructions and required input are available.

The Skill does not launch or drive Notion-side agents or AI sessions. External writes and messages remain subject to your request and the host's authorization requirements. A dry run does not update completion state.

This repository distributes instructions. It does not include an MCP server or a persistent background process. Skill loading and available MCP capabilities depend on the client; compatibility has not been verified across all clients.

## Files

- [SKILL.md](SKILL.md) defines target selection, configuration retrieval, MCP execution, and result verification.
- [Read Custom Agent settings](references/read-configuration.md) covers discovery, configuration versions, and resume state.
- [Read Notion Skills](references/read-skills.md) covers instruction pages and supporting resources.
- [Execute through MCP](references/execute-via-mcp.md) covers tool mapping and execution checks.
- [Agent retrieval](docs/agent-retrieval.md) compares ways to read Custom Agent instructions and settings and records test runs. It is reference material, not part of the Skill's instructions.

## License

[MIT](LICENSE). This is an independent, unofficial project.
