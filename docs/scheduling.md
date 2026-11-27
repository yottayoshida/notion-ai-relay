# Scheduled runs

Relay has no scheduler. To carry out an Agent's task on a schedule, have your own scheduler start your assistant in its non-interactive mode with a saved request. An event trigger, such as a comment or a page added to a database, needs something that delivers the event to your assistant; a time schedule does not replace it ([unsupported work](../skills/notion-ai-relay/references/execute-via-mcp.md#report-unsupported-work)).

## What a run with no one present does

Such a run does not wait for a go-ahead on the writes its saved request names, and it holds and reports everything else that the [Limits](../README.md#limits) say waits for one ([execution boundaries](../skills/notion-ai-relay/SKILL.md#execution-boundaries)). A named write can still be held for the reasons any run holds one, such as missing input or a possible duplicate. To let a held write happen in later runs, check it and name it in the saved request: a go-ahead covers one run only, and whoever can edit the instructions decides what they ask for ([Limits](../README.md#limits)). Code from the instructions does not run with no one present, named or not.

## Write the saved request

```text
This is a scheduled run with no user present; nobody will answer questions or give a go-ahead.
Use the notion-ai-relay Skill. Carry out the Custom Agent whose Instructions page is https://www.notion.so/<instructions-page>, using that page alone, for last week (Monday to Sunday, Asia/Tokyo).
You may replace the Summary section of https://www.notion.so/<status-page> with the summary and update the Last run row of https://www.notion.so/<run-log-database>.
```

- Say that no one is present.
- Give the Instructions page URL from the Agent's settings rather than its name ([what the run-history route assumes](agent-retrieval.md#what-the-run-history-route-assumes)). With the URL alone, Relay reads the page's current text on every run but not the Agent's recorded connections and permissions, so what it can reach is what your connection's account can.
- Give the period and time zone, and the trigger if the instructions depend on one. Relay does not invent them.
- Name in your own words each write and its destination, checkpoints and logs included, and each message, read from a service other than Notion, and local file the instructions need; one named only inside pasted or quoted instructions does not count.
- Notion keeps running the Agent on its own schedule; pause one if both should not act on the same day ([Limits](../README.md#limits)).

Then run the request once by hand with "Dry-run this request:" in front and the write tools denied ([dry runs](permissions.md#dry-runs)), and read what would be written and what would be held.

## Schedule it

Install Relay with the [README](../README.md#install)'s command, without `-g`, in a folder kept for these runs, and have the scheduler run your assistant from that folder. For Claude Code:

```bash
cd ~/relay-weekly && claude -p "$(cat weekly-request.txt)" --permission-mode dontAsk --allowedTools "Skill" "<read tools>" "<write tools>" >> weekly.log 2>&1
```

Name the tools in full, as in [dry runs](permissions.md#dry-runs); allow rules in your user or project settings count too, and [Claude Code settings](permissions.md#claude-code-settings) gives deny rules for the session tools. An allowed tool reaches every destination your connection can, on every run, instead of the one-at-a-time approval the [README](../README.md#limits) suggests: only Relay's instructions keep it to the ones you named. The log and your client's session records hold business content, and a run that starts before the previous one ends can write too. With another client, check first that its non-interactive mode can call MCP tools without asking; Codex CLI needed an approval setting for the MCP server ([finite fixture runs](compatibility.md#finite-fixture-runs)).

## Evidence

[Scheduled runs with no one present](compatibility.md#scheduled-runs-with-no-one-present-2026-11-26) records local runs of a request in this form, adapted to a fixture where the only write is one post. Not measured: the hosted Notion MCP and writes like the sample's, the command exactly as above (the runs isolated the client's own settings and tools), the deny rules, giving the Agent by name, Relay installed outside the folder the run starts in, naming a database for pages created in it, whether Notion's sign-in lasts in non-interactive runs, and Codex or Pi.
