"""Diff two awesome-list markdown files to find added/removed repos."""

from __future__ import annotations

from dataclasses import dataclass, field

from github_curator.parser import RepoRef, parse_markdown_repos


@dataclass
class DiffResult:
    """Result of comparing two lists of repositories."""

    added: list[RepoRef] = field(default_factory=list)
    removed: list[RepoRef] = field(default_factory=list)
    common: list[RepoRef] = field(default_factory=list)


def diff_lists(old_markdown: str, new_markdown: str) -> DiffResult:
    """Compare two markdown texts and return added/removed/common repos.

    Args:
        old_markdown: The older version of the markdown text.
        new_markdown: The newer version of the markdown text.

    Returns:
        DiffResult with added, removed, and common repos.
    """
    old_repos = parse_markdown_repos(old_markdown)
    new_repos = parse_markdown_repos(new_markdown)

    old_keys = {(r.owner.lower(), r.name.lower()): r for r in old_repos}
    new_keys = {(r.owner.lower(), r.name.lower()): r for r in new_repos}

    old_set = set(old_keys.keys())
    new_set = set(new_keys.keys())

    added = [new_keys[k] for k in sorted(new_set - old_set)]
    removed = [old_keys[k] for k in sorted(old_set - new_set)]
    common = [new_keys[k] for k in sorted(old_set & new_set)]

    return DiffResult(added=added, removed=removed, common=common)
