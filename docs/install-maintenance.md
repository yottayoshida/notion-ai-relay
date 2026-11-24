# Identify, update, and roll back an installed Relay

This guide concerns the **Relay files on disk**, not the version of an Agent's instructions retrieved from Notion. Commands below use skills CLI **1.9.0** (Node.js 22.20+); other installer versions may differ. See its [command reference](https://github.com/vercel-labs/skills/blob/v1.9.0/docs/commands.md). Do not update a running task's instructions halfway through a run. The first section is the usual update; the rest is for a copy you cannot identify, a manual copy, and rollback.

## Update the usual way

1. List the releases: `git ls-remote --tags https://github.com/yottayoshida/notion-ai-relay` (or the [releases page](https://github.com/yottayoshida/notion-ai-relay/releases)). `npx skills check` does not report a newer release for a copy pinned to a tag.
2. Install the newest tag with the scope and client options you used before, for example `npx skills add yottayoshida/notion-ai-relay@<tag>`, adding `-g` for a global copy; skills CLI 1.8.0 or later reads a version tag such as `@v1.2.3` as a pin. If `npx skills list --json` marks the copy `modified`, or you changed its files, back it up first as in [section 2](#2-inspect-and-back-up-before-changing-anything).
3. Start a new session and ask the Skill which Relay version it is; [section 5](#5-confirm-reload-and-diagnose-without-secrets) shows which files it loaded.

## Install without the skills CLI

For manual installation, put this repository in your client's Skill directory as a folder named `notion-ai-relay`, the `name` in `SKILL.md`, for example with `git clone --branch <release tag> https://github.com/yottayoshida/notion-ai-relay.git`. A GitHub zip extracts to a folder named after the repository and the tag or branch; rename it, because a client may name the Skill after its folder. Keep `SKILL.md` and `references/` together. `agents/openai.yaml` contains optional Codex display metadata.

## 1. Locate the copy the client actually loads

Run these from the project where you use the Skill:

```bash
npx skills@1.9.0 list --json
npx skills@1.9.0 list -g --json
```

The output includes each installed `path`, scope, and client. Inspect the selected client's Skill inventory too: a project copy can coexist with a global copy. Common paths are `.claude/skills/notion-ai-relay` for Claude Code and `.agents/skills/notion-ai-relay` for Codex, relative to the project or home directory. These are examples, not proof of which copy loaded. Other clients have different discovery rules. Resolve symlinks before comparing or backing up files:

```bash
skill='/absolute/path/from/the/inventory/notion-ai-relay'
python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$skill"
```

For manual installs, find the folder through the client's inventory/configured Skill directories rather than assuming that `list` discovers every custom location. Keep the directory name `notion-ai-relay` and `SKILL.md`, `references/`, and any client metadata together.

### Determine the revision, without guessing

| Installation | Evidence to inspect | What it establishes |
|---|---|---|
| skills CLI, project scope | `skills-lock.json` in the project; entry `skills["notion-ai-relay"]`, plus `list --json` status | `source` and `ref` record the requested source, and skills CLI 1.9.0 also records `commit`, the commit it installed. A full commit ref pins it; `main` or a tag alone is not an immutable revision. `tracked` means installed content matches the lock hash, not that a client loaded it. |
| skills CLI, global scope | `list -g --json`, installation receipt, and comparison with a pinned snapshot below | Do not infer a commit from the directory name or assume the project lock describes a global copy. |
| Dedicated Git clone | Commands below | HEAD identifies the checkout; a dirty checkout is that revision **plus local changes**. |
| ZIP or manual copy | Saved full commit/download URL and comparison with a pinned snapshot | A branch-named ZIP or copied folder without provenance has **unknown revision** until checked. Matching files establishes content equivalence, not unique commit identity. |

Only run these Git commands after confirming the Skill directory itself is the clone root; otherwise Git may report the containing project's HEAD:

```bash
git -C "$skill" rev-parse --show-toplevel
git -C "$skill" rev-parse HEAD
git -C "$skill" status --short
```

To check a claimed commit independently, download/extract its archive as in section 4, then compare it with the resolved installed directory:

```bash
diff -ru --exclude=.git "$snapshot" "$skill"
```

Here `snapshot` is the extracted `notion-ai-relay-<full-commit>` directory. Exit 0 means equal files; exit 1 means differences to inspect. Installers may omit files such as `metadata.json` or Git internals; do not dismiss changes in `SKILL.md`, `references/`, or `agents/`. An old or absent CLI lock cannot reconstruct a lost commit. Record `unknown` rather than inventing a version. `metadata.version` in `SKILL.md` names the release only for a copy installed from that release's tag; a copy of `main` carries the version of the last release before it. The YAML `name` and Notion configuration versions are not Relay revision identifiers.

## 2. Inspect and back up before changing anything

Stop if the directory or scope is not the intended one. Review the diff against the recorded snapshot (and `git diff`/untracked files for a clone). CLI `modified` or `untracked` is a reason to inspect, not permission to discard edits. Even a `tracked` copy should be backed up before replacement.

Create a new backup directory **outside all client Skill directories**; the following assumes it does not already exist:

```bash
backup='/absolute/path/outside/skill-directories/relay-backup-YYYYMMDD-HHMMSS'
mkdir "$backup"
cp -RL "$skill" "$backup/notion-ai-relay"
# For a project CLI installation, from the project root:
if test -f skills-lock.json; then cp skills-lock.json "$backup/skills-lock.json"; fi
```

`cp -RL` saves the contents, including symlink targets, rather than just a link. Also record the original link target, installed path, scope, installer version, and full commit if known. Do not put these notes or backups containing local instructions in a public repository. Keep a dedicated clone's `.git` backup private too. Do not use `reset --hard`, `clean`, or a blanket all-skills update to resolve local edits. Reapply only reviewed local changes after an update; they make the result a modified revision.

## 3. skills CLI: explicit, scoped replacement

The following example updates **one project-scoped Claude Code copy**. Substitute the same client you originally selected (`codex` for Codex). For global scope, add `-g` to **both** installation commands and verify `list -g`. Do not mix scopes or change copy/symlink mode unintentionally. This example explicitly uses copies; retain your original mode if different.

Choose and review a full commit first; do not paste the placeholder literally:

```bash
target='<reviewed-full-commit>'
npx skills@1.9.0 add "yottayoshida/notion-ai-relay@$target" \
  --skill notion-ai-relay -a claude-code --copy -y
npx skills@1.9.0 list --json
```

`-y` permits replacement without another prompt: use it only **after** the backup and diff review above. Check the exit status, installed path, content, and lock `ref`, not just the success banner. To roll back, run the same `add` command with the previously recorded full commit. Then compare with its snapshot and perform section 5 again. If local edits were part of the old installation, a commit rollback does not restore them: recover/review them from the backup separately.

The CLI also offers `check` and `update notion-ai-relay -p` (or `-g`). `check` can exit 1 for updates or local changes; that is not proof of a broken install. For a reproducible change or rollback, use explicit pinned `add` as above rather than assuming `update` selects the commit you intended. Never use unqualified `update` to maintain just Relay.

If the network is unavailable, keep the current installation or restore the saved contents into the same resolved destination after moving the replaced copy aside. Preserve the original link arrangement. Restore a backed-up project lock only if no other skills' lock entries have changed meanwhile; otherwise reconcile just Relay's entry. A file restore is not evidence that the client has reloaded it.

## 4. Git clone, ZIP, or manual copy

### Dedicated Git clone

After the backup, ensure `git status --porcelain` is empty, including untracked files. If not, stop and preserve/reconcile the changes; do not force a checkout. For a clean clone rooted at `$skill`:

```bash
git -C "$skill" fetch origin
git -C "$skill" switch --detach "$target"
git -C "$skill" rev-parse HEAD
git -C "$skill" status --short
```

A detached checkout is intentional: updates will not silently follow a moving branch. Roll back by repeating with the recorded previous full commit. Confirm the remote is the expected repository before fetching. A manual copy inside a larger Git project is **not** a dedicated clone; use the snapshot method instead.

### ZIP or manual copy

Use a full commit rather than `main.zip`. Work in a new staging directory outside Skill discovery:

```bash
staging='/absolute/path/to/new-staging-directory'
mkdir "$staging"
curl -fL "https://github.com/yottayoshida/notion-ai-relay/archive/${target}.zip" \
  -o "$staging/relay.zip"
unzip -q "$staging/relay.zip" -d "$staging"
snapshot="$staging/notion-ai-relay-$target"
test -f "$snapshot/SKILL.md" && test -d "$snapshot/references"
```

Continue only if every command succeeds. Review the staged files and record the full commit. Move the old installed directory to a unique holding path outside Skill discovery, then copy the **whole** snapshot to the original path, named `notion-ai-relay`. Do not overlay new files on old files: removed references would survive. If the destination is a symlink, replace the resolved content deliberately and preserve the link; do not accidentally replace the link alone. Compare installed files with the snapshot afterward.

Rollback uses the same procedure with the previous pinned snapshot, or moves the replaced directory aside and restores the complete backup to the same destination. For a copy with unknown provenance, report “restored backup, revision unknown,” not a guessed commit.

## 5. Confirm reload, and diagnose without secrets

Disk verification and client loading are separate checks:

1. Check the final path, full commit/lock entry and any remaining diff. Ensure no stale project/global duplicate is being selected.
2. End the old conversation and start a fresh client session in the same project. Use that client's documented Skill reload/discovery interface if available; do not assume that replacing files refreshes an existing conversation.
3. Inspect its Skill inventory, then explicitly invoke `notion-ai-relay` for a **read-only diagnostic with no Notion access or external writes**: ask it to read the installed `SKILL.md` and a local reference and identify their paths. Use file-read/tool traces to confirm the resolved paths and contents match the snapshot. A claimed version in the assistant's answer alone is not proof. This check needs no MCP connection.
4. If the client cannot expose loaded paths/content, mark reload **unverified**. Report that limitation rather than claiming compatibility. Live MCP operation requires a separate, authorized test; file loading does not prove connectivity or write/read-back support.

For support, provide only client name/version, model identifier, Relay version and full commit (or unknown/modified), scope, installer version, whether fresh-session loading was observed, and the connection's **capabilities** (for example, listing, full-page reads, writes, and read-after-write). Redact usernames/private paths. Do not send tokens, credential stores, business page contents, or complete conversation logs.

## Validation and limits

See [isolated maintenance checks](../tests/install-maintenance/README.md) for reproducible update/rollback tests and the exact tested revisions. These tests exercise installation files, not a client's Skill discovery or Notion connection. No client reload or live MCP compatibility is claimed by this guide.
