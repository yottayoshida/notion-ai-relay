# Isolated installation maintenance replay

This opt-in, networked test accompanies the [maintenance guide](../../docs/install-maintenance.md). It does not run in the offline structural suite. It installs only into temporary project and HOME directories and removes them on exit. No client session, model, MCP server, or real Notion data is used.

## Prerequisites and invocation

Use Python 3.10+, Node.js 22.20+, npm, Git, curl, unzip, cp, mv, and diff. The commands target a POSIX environment; Windows shell behavior is unverified. Network access is required to npm and the public GitHub repository. Git operations disable system/global Git configuration and use anonymous public access. Run outside any active maintenance operation.

From the repository root, choose a **new disposable directory outside client Skill directories** for `scratch`:

```bash
scratch='/absolute/path/to/new-disposable-directory'
mkdir "$scratch"
npm install --prefix "$scratch/cli" skills@1.8.1 --ignore-scripts --no-audit --no-fund
python3 -B tests/install-maintenance/replay.py \
  --cli "$scratch/cli/node_modules/skills/bin/cli.mjs"
```

The installed CLI entrypoint runs through Node, equivalent to the guide's pinned `npx skills@1.8.1` commands without repeatedly invoking npm. The replay prints commands and assertions; redirect output to a private log if needed. A nonzero exit, timeout, missing dependency, or unavailable network is **not** a PASS. Assertions must remain enabled (do not use Python `-O` or `PYTHONOPTIMIZE`). The CLI download itself is an explicit network dependency, not a model execution or billing path.

## Fixed fixtures and expected outcomes

The source snapshots are public GitHub ZIPs pinned to:

- A: `16fb435eae7074ccf53a7448ea051d519251b353`
- B: `687e9dfd1d9ebfd7d18af6912e5a521bd7603c81`

Their contents differ, including the Codex prompt metadata. Each of four routes performs A → B → A (12 installed states):

| Route | Assertions |
|---|---|
| skills CLI, project copy, Claude Code target | All installed bytes equal the selected snapshot; project lock has the full commit; inventory path matches; status is tracked. |
| skills CLI, global copy, Claude Code target | All installed bytes equal the selected snapshot; global inventory path resolves inside the temporary HOME. No project lock is used as evidence for global scope. |
| Dedicated Git clone | Clean checkout, clone root, detached HEAD and installed bytes match each selected commit. |
| ZIP/manual copy | Whole-directory replacement matches the selected snapshot; a stale file is retained only in the holding copy, not in the new installation. |

Additional checks add a local edit before CLI replacement, verify project `modified` detection, and preserve edited content through `cp -RL` backups. A clone with an untracked file fails the guide's clean-check precondition. A symlink backup contains actual files, not just the link. These are file-operation checks: the replay does not assert that CLI replacement automatically protects local edits or that a dirty Git checkout will always refuse a switch.

## Scope limits

- CLI symlink installation mode and Codex/other client installation targets are not exercised; only copying to the Claude Code target is tested. Symlink **backup** is a separate filesystem check.
- Client discovery, instruction reload, version precedence between project/global copies, and live Notion compatibility require their own observations. Follow section 5 of the guide and mark unavailable checks unverified.
- The temporary directories contain synthetic edits only. Failed runs are not automatically retried; investigate their logs before rerunning.
- These fixed snapshots test update/rollback mechanics. They do not certify a newly edited repository's runtime behavior, a different installer version, or future upstream commits.
