# Files

- [SKILL.md](../SKILL.md) defines target selection, configuration retrieval, MCP execution, and result verification.
- [Read Custom Agent settings](../references/read-configuration.md) covers discovery, configuration versions, and resume state.
- [Read Notion Skills](../references/read-skills.md) covers instruction pages and supporting resources.
- [Execute through MCP](../references/execute-via-mcp.md) covers tool mapping and execution checks.
- [Agent retrieval](agent-retrieval.md) compares ways to read Custom Agent instructions and settings and records test runs. It is reference material, not part of the Skill's instructions.
- [Structural checks](structural-checks.md) covers the CI check.
- Decision cases without a scorer are in `evals/`, where CI checks that each case has a unique `id` and a non-empty expected outcome; `tests/` keeps the suites whose scorers and fixtures CI runs. Each folder has its own replay steps. Neither is runtime instructions.
- [Security-boundary execution cases](../tests/security/README.md) provide a synthetic MCP fixture, attempted-call scoring, and separate host-denial tests.
- [Write lifecycle execution cases](../tests/write-lifecycle/README.md) exercise synthetic writes, unknown outcomes, verification, stop, and resume through a fault-injecting MCP fixture.
- [Client/permission/resource fixtures](../tests/compatibility/README.md) define the finite compatibility replay and pure-comparison boundary checks.
