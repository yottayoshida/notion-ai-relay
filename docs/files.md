# Files

- [SKILL.md](../SKILL.md) defines target selection, configuration retrieval, MCP execution, and result verification.
- [Read Custom Agent settings](../references/read-configuration.md) covers discovery, configuration versions, and resume state.
- [Read Notion Skills](../references/read-skills.md) covers instruction pages and supporting resources.
- [Execute through MCP](../references/execute-via-mcp.md) covers tool mapping and execution checks.
- [Agent retrieval](agent-retrieval.md) compares ways to read Custom Agent instructions and settings and records test runs. It is reference material, not part of the Skill's instructions.
- [Compatibility and evidence](compatibility.md) is the dated matrix of synthetic checks, historical live records, blockers, and unverified environments.
- [Installation maintenance](install-maintenance.md) covers finding the installed copy, updates, backups, rollback, and what to send for support.
- [Security policy](../SECURITY.md) says what to report privately and where.
- [Structural checks](structural-checks.md) covers the CI check. `scripts/` holds the check and the command CI runs.
- Decision cases without a scorer are in `evals/`, where CI checks that each case has a unique `id` and a non-empty expected outcome; `tests/` keeps the suites whose scorers and fixtures CI runs. Each folder has its own replay steps. Neither is runtime instructions.
- [Security-boundary execution cases](../tests/security/README.md) provide a synthetic MCP fixture, attempted-call scoring, and separate host-denial tests.
- [Write lifecycle execution cases](../tests/write-lifecycle/README.md) exercise synthetic writes, unknown outcomes, verification, stop, and resume through a fault-injecting MCP fixture.
- [Resume-handoff cases](../tests/resume-handoff/README.md) check resuming interrupted work and the handoff returned when work stops.
- [Response-language cases](../tests/response-language/README.md) check the language of replies and of content for destinations against supplied snapshots.
- [Client/permission/resource fixtures](../tests/compatibility/README.md) define the finite compatibility replay and pure-comparison boundary checks.
- [Installation maintenance replay](../tests/install-maintenance/README.md) is an opt-in, networked replay of installing and updating into temporary directories; CI does not run it.
- `.github/` holds the CI workflow, the issue form, and the Dependabot settings.
