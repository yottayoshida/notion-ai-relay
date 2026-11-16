#!/usr/bin/env python3
"""Opt-in networked installation checks; never use real client directories."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

OLD = "16fb435eae7074ccf53a7448ea051d519251b353"
NEW = "687e9dfd1d9ebfd7d18af6912e5a521bd7603c81"
REPO = "https://github.com/yottayoshida/notion-ai-relay.git"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, required=True,
                        help="skills 1.8.1 bin/cli.mjs, with dependencies installed")
    args = parser.parse_args()
    cli = args.cli.resolve()
    if not cli.is_file():
        parser.error("--cli must be an installed skills CLI entrypoint")

    with tempfile.TemporaryDirectory(prefix="relay-maintenance-") as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        env = dict(os.environ, HOME=str(home), DISABLE_TELEMETRY="1",
                   DO_NOT_TRACK="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")
        for name in ("GITHUB_TOKEN", "GH_TOKEN", "GIT_DIR", "GIT_WORK_TREE",
                     "XDG_CONFIG_HOME", "XDG_DATA_HOME", "AGENTS_HOME"):
            env.pop(name, None)
        env["XDG_CONFIG_HOME"] = str(home / ".config")
        env["XDG_DATA_HOME"] = str(home / ".local/share")

        def run(*command, cwd=root):
            print("+", " ".join(map(str, command)), flush=True)
            result = subprocess.run(list(map(str, command)), cwd=cwd, env=env,
                                    text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=120)
            print(result.stdout, end="", flush=True)
            print(result.stderr, end="", flush=True)
            result.check_returncode()
            return result.stdout

        def files(path):
            return {str(p.relative_to(path)): p.read_bytes()
                    for p in path.rglob("*") if p.is_file()
                    and ".git" not in p.relative_to(path).parts}

        snapshots = {}
        for revision in (OLD, NEW):
            archive = root / f"{revision}.zip"
            run("curl", "-fL", f"https://github.com/yottayoshida/notion-ai-relay/archive/{revision}.zip",
                "-o", archive)
            run("unzip", "-q", archive, "-d", root)
            snapshots[revision] = root / f"notion-ai-relay-{revision}"
            assert (snapshots[revision] / "SKILL.md").is_file()
            assert (snapshots[revision] / "references").is_dir()
        assert files(snapshots[OLD]) != files(snapshots[NEW])

        # Every scope checks the installed bytes and lock, not the install banner.
        for scope in ("project", "global"):
            project = root / scope
            project.mkdir()
            scope_args = ["-g"] if scope == "global" else []
            installed = ((home if scope == "global" else project)
                         / ".claude/skills/notion-ai-relay")
            for index, revision in enumerate((OLD, NEW, OLD)):
                run("node", cli, "add", f"yottayoshida/notion-ai-relay@{revision}",
                    "--skill", "notion-ai-relay", "-a", "claude-code", "--copy",
                    "-y", *scope_args, cwd=project)
                assert files(installed) == files(snapshots[revision])
                inventory = json.loads(run("node", cli, "list", "--json",
                                           *scope_args, cwd=project))
                entry = next(item for item in inventory
                             if item["name"] == "notion-ai-relay")
                assert Path(entry["path"]).resolve() == installed.resolve()
                if scope == "project":
                    lock = json.loads((project / "skills-lock.json").read_text())
                    assert lock["skills"]["notion-ai-relay"]["ref"] == revision
                    assert entry["status"] == "tracked"
                if index == 0:
                    with (installed / "SKILL.md").open("a") as stream:
                        stream.write("\nLocal maintenance-test note.\n")
                    backup = root / f"{scope}-backup"
                    run("cp", "-RL", installed, backup)
                    assert files(backup) == files(installed)
                    if scope == "project":
                        changed = json.loads(run("node", cli, "list", "--json", cwd=project))
                        assert next(item for item in changed if item["name"] == "notion-ai-relay")["status"] == "modified"
                    # The reviewed local edit is preserved in the backup, not silently lost.
                    assert b"Local maintenance-test note." in (backup / "SKILL.md").read_bytes()
                print(f"PASS CLI {scope}: {revision}", flush=True)

        clone = root / "git-install" / "notion-ai-relay"
        run("git", "clone", REPO, clone)
        assert Path(run("git", "-C", clone, "rev-parse", "--show-toplevel").strip()).resolve() == clone.resolve()
        for revision in (OLD, NEW, OLD):
            assert run("git", "-C", clone, "status", "--porcelain").strip() == ""
            run("git", "-C", clone, "fetch", "origin")
            run("git", "-C", clone, "switch", "--detach", revision)
            assert run("git", "-C", clone, "rev-parse", "HEAD").strip() == revision
            assert files(clone) == files(snapshots[revision])
            print(f"PASS Git: {revision}", flush=True)
        (clone / "local-note.txt").write_text("preserve me\n")
        assert run("git", "-C", clone, "status", "--porcelain").strip()
        print("PASS dirty-clone detection: untracked file blocks documented clean-check precondition")

        manual = root / "manual" / "notion-ai-relay"
        manual.parent.mkdir()
        for index, revision in enumerate((OLD, NEW, OLD)):
            if manual.exists():
                run("mv", manual, root / f"manual-holding-{index}")
            run("cp", "-R", snapshots[revision], manual)
            run("diff", "-ru", "--exclude=.git", snapshots[revision], manual)
            assert files(manual) == files(snapshots[revision])
            if index == 0:
                (manual / "obsolete-local-file.txt").write_text("keep only in holding copy\n")
            print(f"PASS ZIP/manual: {revision}", flush=True)
        assert (root / "manual-holding-1/obsolete-local-file.txt").is_file()
        assert not (manual / "obsolete-local-file.txt").exists()

        link = root / "linked-skill"
        link.symlink_to(manual, target_is_directory=True)
        backup = root / "link-backup"
        run("cp", "-RL", link, backup)
        assert not backup.is_symlink()
        assert files(backup) == files(manual)
        print("PASS symlink-content backup")
        print("PASS all 12 installation states and backup/dirty/stale-file checks; no client or MCP launched")


if __name__ == "__main__":
    main()
