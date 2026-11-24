from pathlib import Path, PurePosixPath
import unittest

from scripts.check_structure import MARKDOWN, local_target, markdown_info, repository_files


REPOSITORY = Path(__file__).resolve().parents[1]
GUIDE = REPOSITORY / "docs/files.md"
FOLDERS = ("scripts/", "evals/", ".github/")


def must_link(name):
    path = PurePosixPath(name)
    if path.suffix != ".md":
        return False
    if len(path.parts) == 1:
        return name != "README.md"
    if path.parts[0] in {"references", "docs"} and len(path.parts) == 2:
        return name != "docs/files.md"
    return path.parts[0] == "tests" and len(path.parts) == 3 and path.name == "README.md"


def guide_references(text):
    _, links = markdown_info(text)
    targets = set()
    for url in links:
        target = local_target(REPOSITORY, GUIDE, url)
        if target is not None:
            targets.add(target.relative_to(REPOSITORY).as_posix() + ("/" if target.is_dir() else ""))
    spans = {child.content for token in MARKDOWN.parse(text) for child in token.children or [] if child.type == "code_inline"}
    return targets, spans


class FileGuideTests(unittest.TestCase):
    def test_the_file_guide_points_to_every_distributed_document_and_folder(self):
        targets, spans = guide_references(GUIDE.read_text(encoding="utf-8"))
        unlinked = sorted(name for name in repository_files(REPOSITORY) if must_link(name) and name not in targets)
        unmentioned = [folder for folder in FOLDERS if not any(item.startswith(folder) for item in targets | spans)]
        self.assertEqual((unlinked, unmentioned), ([], []))


if __name__ == "__main__":
    unittest.main()
