# Troubleshooting

When a run cannot go on, its report says what to do next: inside the output format you or the procedure fixed, if that format has a place for it, or else in its first lines. This page lists the usual causes behind those reports. The Skill does not load it.

Notion's plans and settings below were checked against Notion's own pages on 2026-11-24 and can change.

| What you see | Likely cause | What to do |
|---|---|---|
| The assistant has no Notion tools | Notion MCP is not connected in this assistant | Connect it as described in [Connect to Notion MCP](https://developers.notion.com/docs/get-started-with-mcp), then ask again |
| Agent tools, such as the Agent search, are missing | The connection lacks the "View sessions and interact with agents" capability | Disconnect and reconnect Notion, or enable the capability in the integration's settings and authorize again ([tools reference](https://developers.notion.com/guides/mcp/tools-skills-agents-reference)) |
| An Agent tool is refused, with a link | Custom Agents need a Business or Enterprise plan ([Notion help](https://www.notion.com/help/custom-agents)), and the tools need Notion AI access and access to Custom Agents ([tools reference](https://developers.notion.com/guides/mcp/tools-skills-agents-reference)) | The report passes on the refusal's link with the tool that refused and the site the link goes to; open it if it goes to Notion. The Skill does not change settings for you unless you ask |
| The Agent is not found | It is not shared with you, or its name differs | Check in Notion that the Agent is shared with you and how it is named, or give its URL |
| It asks for the Instructions page link or the text | No reader for Agent settings, and no usable chat of yours or scheduled run ([Agent retrieval](agent-retrieval.md)) | In Notion, open the Agent's settings and copy the link to its Instructions page, or paste the instructions |
| A write is held because you cannot edit the destination | You can only view that page or database | Ask someone with full access to give you edit access, or name another destination |
| It asks you to paste a file | Notion MCP returned the file only as a download URL, and this client cannot download it or extract the archive | Paste the file's content, or use a client that can download it |
