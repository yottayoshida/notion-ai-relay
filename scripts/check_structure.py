"""Validate the distributed Skill, not model behavior or MCP compatibility."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import tempfile
import unicodedata
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
import yaml


SKILL_NAME = "notion-ai-relay"
REQUIRED = (
    "SKILL.md", "README.md", "LICENSE", "agents/openai.yaml",
    "references/read-configuration.md", "references/read-skills.md",
    "references/execute-via-mcp.md", "docs/agent-retrieval.md",
)
PACKAGE_ENTRIES = ("SKILL.md", "README.md", "LICENSE", "references", "agents", "docs", "assets")
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


class HtmlIds(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        self.ids.update(value for key, value in attrs if key == "id" or (tag == "a" and key == "name"))


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
            parser = HtmlIds()
            parser.feed(fragment.content)
            anchors.update(parser.ids)
    return anchors, links


def local_target(root, source, url):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        return None
    target = (source.parent / unquote(parsed.path)).resolve() if parsed.path else source.resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"local reference escapes Skill directory: {url}")
    if not target.is_file():
        raise ValueError(f"missing local reference: {url}")
    if parsed.fragment:
        if target.suffix.lower() != ".md":
            raise ValueError(f"cannot validate anchor in non-Markdown file: {url}")
        text = target.read_text(encoding="utf-8")
        if target.name == "SKILL.md":
            _, text = frontmatter(text)
        anchors, _ = markdown_info(text)
        if unquote(parsed.fragment) not in anchors:
            raise ValueError(f"missing anchor: {url}")
    return target


def validate(root):
    root = Path(root)
    for relative in REQUIRED:
        if not (root / relative).is_file():
            raise ValueError(f"missing required file: {relative}")
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

    yamls = sorted(set(root.rglob("*.yaml")) | set(root.rglob("*.yml")))
    for path in yamls:
        load_yaml(path.read_text(encoding="utf-8"))
    config = load_yaml((root / "agents/openai.yaml").read_text(encoding="utf-8"))
    interface = config.get("interface")
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
            if not isinstance(url, str) or not url.strip() or local_target(root, root / "SKILL.md", url) is None:
                raise ValueError(f"openai.yaml {key} must reference a local asset")

    markdowns = sorted(root.rglob("*.md"))
    link_count = 0
    for path in markdowns:
        text = path.read_text(encoding="utf-8")
        if path.name == "SKILL.md":
            _, text = frontmatter(text)
        _, links = markdown_info(text)
        for url in links:
            try:
                if local_target(root, path, url) is not None:
                    link_count += 1
            except ValueError as error:
                raise ValueError(f"{path.relative_to(root)}: {error}") from error
    check_codex_quoting(yaml.compose((root / "agents/openai.yaml").read_text(encoding="utf-8")))
    return len(markdowns), len(yamls), link_count


def stage(source, destination):
    for entry in PACKAGE_ENTRIES:
        path = source / entry
        if path.is_dir():
            shutil.copytree(path, destination / entry)
        elif path.is_file():
            shutil.copy2(path, destination / entry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=Path, help="validate an existing installation instead of staging the repository")
    args = parser.parse_args()
    try:
        if args.skill_dir:
            counts = validate(args.skill_dir)
        else:
            with tempfile.TemporaryDirectory() as temp:
                destination = Path(temp) / SKILL_NAME
                destination.mkdir()
                stage(Path(__file__).resolve().parents[1], destination)
                counts = validate(destination)
    except (ValueError, yaml.YAMLError, OSError, TypeError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print(f"PASS: {counts[0]} Markdown files, {counts[1]} YAML files, {counts[2]} local references; structure only")


if __name__ == "__main__":
    main()
