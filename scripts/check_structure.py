"""Validate the distributed Skill folder and the repository's documents, not model behavior or MCP compatibility."""

import argparse
from contextlib import contextmanager
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unicodedata
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
import yaml


SKILL_NAME = "notion-ai-relay"
SKILL_DIR = Path("skills") / SKILL_NAME
REQUIRED = (
    "SKILL.md", "LICENSE", "agents/openai.yaml",
    "references/discover.md", "references/read-configuration.md", "references/read-skills.md",
    "references/execute-via-mcp.md",
)
REPOSITORY_REQUIRED = ("README.md", "LICENSE", "docs/agent-retrieval.md")
FRONTMATTER_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
MARKDOWN = MarkdownIt("commonmark")


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError(f"duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def load_yaml(text):
    value = yaml.load(text, Loader=UniqueLoader)
    if not isinstance(value, dict):
        raise ValueError("expected a YAML mapping")
    return value


def frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError("missing YAML frontmatter delimiters")
    end = lines.index("---", 1)
    return load_yaml("\n".join(lines[1:end])), "\n".join(lines[end + 1:])


def check_codex_quoting(node, visited=None):
    visited = set() if visited is None else visited
    if id(node) in visited:
        return
    visited.add(id(node))
    if isinstance(node, yaml.MappingNode):
        for key, value in node.value:
            if key.style is not None:
                raise ValueError("openai.yaml keys must be unquoted")
            check_codex_quoting(value, visited)
    elif isinstance(node, yaml.SequenceNode):
        for value in node.value:
            check_codex_quoting(value, visited)
    elif node.tag == "tag:yaml.org,2002:str" and node.style not in {'"', "'"}:
        raise ValueError("openai.yaml string values must be quoted")


@contextmanager
def about(relative):
    try:
        yield
    except (ValueError, yaml.YAMLError, TypeError) as error:
        raise ValueError(f"{relative}: {error}") from error


class HtmlTags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links = set(), []

    def handle_starttag(self, tag, attrs):
        self.ids.update(value for key, value in attrs if key == "id" or (tag == "a" and key == "name"))
        self.links.extend(value for key, value in attrs
                          if value and ((tag == "a" and key == "href") or (tag == "img" and key == "src")))


def markdown_info(text):
    tokens = MARKDOWN.parse(text)
    anchors, links = set(), []
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            children = tokens[index + 1].children or []
            title = "".join(child.content for child in children if child.type in {"text", "code_inline"})
            slug = "".join(
                char for char in title.lower()
                if char in "-_ " or unicodedata.category(char)[0] not in "PS"
            ).replace(" ", "-")
            candidate, suffix = slug, 0
            while candidate in anchors:
                suffix += 1
                candidate = f"{slug}-{suffix}"
            anchors.add(candidate)
        for child in token.children or []:
            if child.type in {"link_open", "image"}:
                links.append(child.attrGet("href") if child.type == "link_open" else child.attrGet("src"))
        html = [token] if token.type == "html_block" else [child for child in token.children or [] if child.type == "html_inline"]
        for fragment in html:
            parser = HtmlTags()
            parser.feed(fragment.content)
            anchors.update(parser.ids)
            links.extend(parser.links)
    return anchors, links


def markdown_text(path):
    text = path.read_text(encoding="utf-8")
    return frontmatter(text)[1] if path.name == "SKILL.md" else text


def local_target(root, source, url, boundary="Skill directory"):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        return None
    target = (source.parent / unquote(parsed.path)).resolve() if parsed.path else source.resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"local reference escapes {boundary}: {url}")
    if not target.exists():
        raise ValueError(f"missing local reference: {url}")
    if parsed.fragment:
        if target.suffix.lower() != ".md":
            raise ValueError(f"cannot validate anchor in non-Markdown file: {url}")
        with about(target.relative_to(root.resolve())):
            anchors, _ = markdown_info(markdown_text(target))
        if unquote(parsed.fragment) not in anchors:
            raise ValueError(f"missing anchor: {url}")
    return target


def empty(value):
    if isinstance(value, str):
        return not value.strip()
    return value is None or value == [] or value == {}


def check_eval_cases(root):
    folders = sorted(path for path in (Path(root) / "evals").iterdir() if path.is_dir())
    for folder in folders:
        path = folder / "cases.json"
        if not path.is_file():
            raise ValueError(f"{folder.relative_to(root)}: missing cases.json")
        with about(path.relative_to(root)):
            value = json.loads(path.read_text(encoding="utf-8"))
        cases = value.get("cases") if isinstance(value, dict) else value
        if not isinstance(cases, list) or not cases:
            raise ValueError(f"{path.relative_to(root)}: no cases")
        seen = set()
        for case in cases:
            if not isinstance(case, dict):
                raise ValueError(f"{path.relative_to(root)}: case is not an object: {case!r}")
            case_id = case.get("id")
            if not isinstance(case_id, str) or not case_id or case_id in seen:
                raise ValueError(f"{path.relative_to(root)}: missing or duplicate id {case_id!r}")
            seen.add(case_id)
            if not any(key.startswith("expected") and not empty(case[key]) for key in case):
                raise ValueError(f"{path.relative_to(root)}: case {case_id} has no expected outcome")
    return len(folders)


def require(root, relatives):
    for relative in relatives:
        if not (root / relative).is_file():
            raise ValueError(f"missing required file: {relative}")


def check_yaml_files(root):
    yamls = sorted(set(root.rglob("*.yaml")) | set(root.rglob("*.yml")))
    for path in yamls:
        with about(path.relative_to(root)):
            load_yaml(path.read_text(encoding="utf-8"))
    return len(yamls)


def check_markdown_links(root, boundary):
    markdowns = sorted(root.rglob("*.md"))
    link_count = 0
    for path in markdowns:
        with about(path.relative_to(root)):
            _, links = markdown_info(markdown_text(path))
            for url in links:
                if local_target(root, path, url, boundary) is not None:
                    link_count += 1
    return len(markdowns), link_count


def validate(root):
    # Not resolve(): a copy reached through a symlink must keep the name it was installed under.
    root = Path(os.path.abspath(root))
    require(root, REQUIRED)
    with about("SKILL.md"):
        name = check_skill_metadata(root)
    yaml_count = check_yaml_files(root)
    with about("agents/openai.yaml"):
        check_codex_metadata(root, name)
    markdown_count, link_count = check_markdown_links(root, "Skill directory")
    return markdown_count, yaml_count, link_count


def validate_repository(root):
    root = Path(os.path.abspath(root))
    require(root, REPOSITORY_REQUIRED)
    yaml_count = check_yaml_files(root)
    if (root / "evals").is_dir():
        check_eval_cases(root)
    markdown_count, link_count = check_markdown_links(root, "repository")
    return markdown_count, yaml_count, link_count


def check_skill_metadata(root):
    metadata, _ = frontmatter((root / "SKILL.md").read_text(encoding="utf-8"))
    if set(metadata) - FRONTMATTER_FIELDS:
        raise ValueError("unexpected frontmatter fields")
    name = metadata.get("name")
    if not isinstance(name, str):
        raise ValueError("invalid frontmatter name")
    name = unicodedata.normalize("NFKC", name.strip())
    if (not 1 <= len(name) <= 64 or name != name.lower()
            or name.startswith("-") or name.endswith("-") or "--" in name
            or not all(char == "-" or char.isalnum() for char in name)):
        raise ValueError("invalid frontmatter name")
    if name != unicodedata.normalize("NFKC", root.name):
        raise ValueError(f"Skill name {name!r} does not match folder {root.name!r}")
    for key, limit in (("description", 1024), ("compatibility", 500)):
        if key == "description" or key in metadata:
            value = metadata.get(key)
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"invalid frontmatter {key}: expected 1-{limit} characters")
    for key in ("license", "allowed-tools"):
        if key in metadata and not isinstance(metadata[key], str):
            raise ValueError(f"frontmatter {key} must be a string")
    if "metadata" in metadata:
        value = metadata["metadata"]
        if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
            raise ValueError("frontmatter metadata must map strings to strings")
    return name


def check_codex_metadata(root, name):
    source = (root / "agents/openai.yaml").read_text(encoding="utf-8")
    interface = load_yaml(source).get("interface")
    if not isinstance(interface, dict):
        raise ValueError("openai.yaml requires interface metadata")
    for key in ("display_name", "short_description", "default_prompt"):
        if not isinstance(interface.get(key), str) or not interface[key].strip():
            raise ValueError(f"openai.yaml requires interface.{key}")
    if not 25 <= len(interface["short_description"]) <= 64:
        raise ValueError("openai.yaml short_description must be 25-64 characters")
    if not re.search(r"\$" + re.escape(name) + r"(?![\w-])", interface["default_prompt"]):
        raise ValueError("openai.yaml default_prompt must reference $" + name)
    if "brand_color" in interface:
        color = interface["brand_color"]
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("openai.yaml brand_color must be a hex color")
    for key in ("icon_small", "icon_large"):
        if key in interface:
            url = interface[key]
            target = local_target(root, root / "SKILL.md", url) if isinstance(url, str) and url.strip() else None
            if target is None or not target.is_file():
                raise ValueError(f"openai.yaml {key} must reference a local asset")
    check_codex_quoting(yaml.compose(source))


def repository_files(source):
    # Not a fixed list of folders: a folder left off it would ship, or stay in the repository, unchecked.
    try:
        listing = subprocess.run(
            ["git", "-C", str(source), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(f"cannot list repository files with git in {source}") from error
    return [os.fsdecode(name) for name in listing.split(b"\0") if name]


def stage(source, destination, names=None):
    for name in repository_files(source) if names is None else names:
        path = source / name
        # Skip what is not a regular file in the working tree (a deletion not yet
        # committed, a submodule); copying it would fail. Skip metadata.json too:
        # the skills CLI drops it, so a link to it would pass here and break once installed.
        if not path.is_file() or path.name == "metadata.json":
            continue
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def listed_by_git(source):
    try:
        return repository_files(source)
    except ValueError:
        return []


def validate_staged(source, name, names=None):
    with tempfile.TemporaryDirectory() as temp:
        destination = Path(temp) / name
        destination.mkdir()
        stage(source, destination, names)
        return validate(destination)


def describe(counts):
    return f"{counts[0]} Markdown files, {counts[1]} YAML files, {counts[2]} local references"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=Path, help="validate an existing installation instead of staging the repository")
    args = parser.parse_args()
    try:
        if args.skill_dir:
            root = Path(os.path.abspath(args.skill_dir))
            # Not rglob over a checkout: it reaches .venv and .claude, which an install never copies. Not a test
            # for root/.git either: the Skill folder sits below the top of its checkout.
            names = listed_by_git(root)
            summary = describe(validate_staged(root, root.name, names) if names else validate(root))
        else:
            with tempfile.TemporaryDirectory() as temp:
                staged = Path(temp) / "repository"
                staged.mkdir()
                stage(Path(__file__).resolve().parents[1], staged)
                summary = (f"distribution {describe(validate(staged / SKILL_DIR))}; "
                           f"repository {describe(validate_repository(staged))}")
    except (ValueError, yaml.YAMLError, OSError, TypeError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print(f"PASS: {summary}; structure only")


if __name__ == "__main__":
    main()
