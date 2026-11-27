# Duplicate-prevention evaluation cases

These cases evaluate the decisions made by an assistant loading `SKILL.md` and `references/`. They use synthetic MCP histories, not real service calls. They do not establish a server's atomicity or end-to-end client compatibility. Run the same histories against the two instruction revisions being compared; record the model, settings, source hashes, decisions, and failures outside the repository.

Unless stated otherwise, the source procedure explicitly requires at most one creation for each business key, input period, and destination across all concurrent runs and delegates. The user's request names each creation and send and its destination. The tool capabilities in each case's `history` are fixture assumptions, not claims about hosted Notion MCP. A readback verifies an effect but cannot prevent a competing creation.

The cases are in `cases.json`. Each has an `id`, its `name`, the synthetic `history` with the available capabilities, and the `expected` decision.

To replay, give the model the instruction files, the fixture assumptions above, and each case's `history`; withhold `expected`. The histories that start with "Same procedure and capabilities" reuse the procedure sentence and the capabilities of `plain-lookup-absent` ("create today's page unless one with the same title exists"; only lookup, ordinary create, and readback): give those, not that case's lookup result.

A passing synthetic decision must cover every actor in the history and distinguish allowed, held, and unknown work. For a live MCP evaluation, additionally interleave two actual callers, inspect the external effect count and contents, and verify the documented key retention and ownership behavior. Do not report the synthetic cases as that live test.
