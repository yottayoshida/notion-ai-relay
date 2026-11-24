# Notion AI Relay

Run Notion agents and skills through MCP.

Notion AI Relay is an Agent Skill that reads the instructions of a Notion Custom Agent or Notion Skill and lets your current AI assistant carry out the work through MCP. It reads each target at runtime instead of storing its workflow in this repository.

## Install

Install with the [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add yottayoshida/notion-ai-relay
```

For manual installation, put this repository in your client's Skill directory as a folder named `notion-ai-relay`, the `name` in `SKILL.md`, for example with `git clone https://github.com/yottayoshida/notion-ai-relay.git`. A GitHub zip extracts to `notion-ai-relay-main`; rename it, because a client may name the Skill after its folder. Keep `SKILL.md` and `references/` together. `agents/openai.yaml` contains optional Codex display metadata.

For installed-file version checks, safe updates, backups, and rollback, see [installation maintenance](docs/install-maintenance.md).

Connect Notion MCP in your AI assistant separately. If a workflow uses another service, connect an MCP server that supports the required operations for that service.

## Use

After your assistant loads the Skill, specify the target and the input for this run. You need not write in English: the [response-language rules](SKILL.md#response-language) set the language of replies and of content written to destinations.

For a Custom Agent, its name or URL is enough when your connection can read the recorded settings of a chat you had with it or one of its scheduled runs, among its latest 60 runs: the Skill reads the Instructions page set in the Agent's settings if your chat recorded it, or else the newest published page recorded, and reports which page and run it used. Notion can cut a run's recorded settings short; the Skill then reports the missing settings as unknown, or asks for the page URL if the cut hides the page link. Otherwise give the Instructions page URL (the link in the Agent's settings) or paste the text. When instructions or settings come from a recorded run, the Skill lists the write destinations, except those you name in the request, and waits for your go-ahead before the first write. [Agent retrieval](docs/agent-retrieval.md) compares the routes.

```text
List the Notion Custom Agents and Notion Skills I can access.
```

Execution and dry-run examples:

```text
Carry out this Custom Agent's task.
Agent: <name or URL>
Input: <target page, time period, and other required input>

Use this Notion Skill to process the supplied material.
Skill URL: <instruction page URL>
Material: <document URL or text>

Dry-run this agent's task without writing to external services.
Agent: <name or URL>
Input: <items to process>
```

## Requirements and limits

The Skill maps each operation to the MCP tools and argument schemas exposed by your environment. It does not require Computer Use, browser automation, a particular operating system, or a client-specific automation API. When Notion MCP returns a download URL for a file in the same run, such as a file uploaded to a page, the Skill downloads it instead of asking you to paste it, in a client that can download it and, for an archive, extract it; no other URL is downloaded outside MCP.

| Operation | Required information or capability |
|---|---|
| List Custom Agents | An MCP agent-listing capability. Results cover the scope exposed by the connection |
| List Notion Skills | An MCP Skill-listing capability, or a known Skill page or database. The hosted Notion MCP lists only Skills enabled for external MCP clients |
| Carry out a Custom Agent's task | Its instructions, a verified or user-supplied link to the target, required settings and input, and the necessary MCP operations |
| Carry out a Notion Skill's task | Its instruction page, required references and attachments, current input, and the necessary MCP operations |
| Run on a schedule | A separately configured scheduler or event receiver |

Some MCP connections cannot retrieve full Agent settings. The Skill then uses the Agent's runs as described under Use; failing that, provide an instruction-page URL, the instruction text, or the missing settings. Pasted text and the editable Instructions page are not treated as a verified current published version. Missing registration or enabled-state metadata does not prevent execution of an explicitly selected procedure when its instructions and required input are available.

The Skill does not launch or drive Notion-side agents or AI sessions. External writes and messages remain subject to your request and the host's authorization requirements. A dry run does not update completion state.

This repository distributes instructions. It does not provide a production MCP server or a persistent background process; synthetic fixture servers under `tests/` are evaluation-only. Skill loading and available MCP capabilities depend on the client; compatibility has not been verified across all clients. See the dated [compatibility matrix](docs/compatibility.md).

## Files

See the [file guide](docs/files.md).

## License

[MIT](LICENSE). This is an independent, unofficial project.
