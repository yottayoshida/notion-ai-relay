# Changelog

Notable changes to Notion AI Relay. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- The rule against mentioning runs other people started now has its own section and applies wherever the Skill reads an Agent's run history, including the question about which run to resume and the report that no run was usable. A resume question offers only runs you may open, identified by date, type and version ([#78](https://github.com/yottayoshida/notion-ai-relay/issues/78)).
- `SKILL.md` now sends a request to list Custom Agents to the new `references/discover.md`, about 670 words, instead of `references/read-configuration.md` and, for the pagination rule, `references/execute-via-mcp.md`. The Agent listing rules moved there, and the section on retrieval completeness is copied there word for word and stays where execution reads it; a test keeps the copies identical. Rules for every read, such as the rate-limit rule, stay in the execution procedure, and listing Notion Skills still uses `references/read-skills.md`. A table in `SKILL.md` says which reference to read for listing, for reading an Agent's settings or a Skill, and for carrying out a task. No rule changed; reinstall to get the new file ([#70](https://github.com/yottayoshida/notion-ai-relay/issues/70)).
- The README now opens with what Relay does and why: your assistant does the work instead of Notion running the Agent on its creator's Select credits, then the workspace's if an owner allows it. It lists requirements before installing, including the Notion plan Custom Agents need, gives three steps for running an Agent, by name, by its Instructions page or by pasted text, and calls this Skill Relay ([#65](https://github.com/yottayoshida/notion-ai-relay/issues/65)).
- The README's limits are now stated as what Relay tells your assistant to do, with only the client's permission settings able to stop a call, and it gives Claude Code settings that deny the session tools Relay is told not to call, tested on a local fixture in four permission modes. It says that writes use each connection's account, that the Agent's own schedule keeps running, and to try a dry run first; [permissions](docs/permissions.md) holds the details ([#66](https://github.com/yottayoshida/notion-ai-relay/issues/66)).

## [0.1.0] - 2026-11-25

First tagged release. Earlier installs followed `main` and carry no version; for what changed since a given commit, compare it with this tag.

### Added

- Discovery of the Notion Custom Agents and Notion Skills a connection can access, and runs, dry runs and resumed runs of their instructions through MCP, with the instructions read at run time.
- Before the first write, message, non-Notion connection, local file or command the user did not name, the Skill lists them, with what each write would contain and from what, and waits for a go-ahead, whichever route supplied the instructions ([#58](https://github.com/yottayoshida/notion-ai-relay/issues/58)).
- Code from the instructions, their files or the data runs only when the user asks for that script and approves its command line; otherwise its calculation is reproduced by reading it ([#59](https://github.com/yottayoshida/notion-ai-relay/issues/59)).
- Files a Notion MCP tool returns are downloaded only over `https` from a host name, without following redirects; from a tar archive of at most 100 members only regular files up to 1 MB whose name appears once are taken ([#59](https://github.com/yottayoshida/notion-ai-relay/issues/59)).
- A release version in `SKILL.md`, which the Skill names when asked which Relay version ran ([#60](https://github.com/yottayoshida/notion-ai-relay/issues/60)).

[Unreleased]: https://github.com/yottayoshida/notion-ai-relay/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yottayoshida/notion-ai-relay/releases/tag/v0.1.0
