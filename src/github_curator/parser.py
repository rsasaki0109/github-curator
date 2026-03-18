"""Parse GitHub repository URLs from markdown files."""

from __future__ import annotations

import re
from typing import NamedTuple


class RepoRef(NamedTuple):
    """A reference to a GitHub repository extracted from text."""

    owner: str
    name: str
    url: str


# Matches github.com/owner/repo in markdown links or plain text.
# Avoids matching deeper paths like github.com/owner/repo/issues.
_GITHUB_REPO_RE = re.compile(
    r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?=[/)\]\s,#]|$)"
)

# Sub-paths that indicate the URL is not pointing to a repo root
_NON_REPO_SUFFIXES = {
    "issues",
    "pull",
    "pulls",
    "actions",
    "wiki",
    "releases",
    "blob",
    "tree",
    "commit",
    "commits",
    "compare",
    "settings",
    "stargazers",
    "network",
    "graphs",
}


def parse_markdown_repos(markdown_text: str) -> list[RepoRef]:
    """Extract unique GitHub repository URLs from markdown text.

    Args:
        markdown_text: Raw markdown string.

    Returns:
        Deduplicated list of RepoRef in order of first appearance.
    """
    seen: set[tuple[str, str]] = set()
    repos: list[RepoRef] = []

    for match in _GITHUB_REPO_RE.finditer(markdown_text):
        owner = match.group(1)
        name = match.group(2)

        # Strip trailing punctuation that the regex might have captured
        name = name.rstrip(".")

        # Skip if this looks like a non-repo page (e.g. the 'repo' part is 'issues')
        if name.lower() in _NON_REPO_SUFFIXES:
            continue

        key = (owner.lower(), name.lower())
        if key not in seen:
            seen.add(key)
            repos.append(RepoRef(owner=owner, name=name, url=f"https://github.com/{owner}/{name}"))

    return repos


def extract_star_count(line: str) -> int | None:
    """Try to extract an existing star count from a markdown line.

    Looks for patterns like:
      - ⭐ 1234
      - Stars: 1,234
      - ![Stars](...) followed by a number
      - (1234 stars)
    """
    patterns = [
        r"[⭐★]\s*([\d,]+)",
        r"[Ss]tars?[:\s]+([\d,]+)",
        r"\(([\d,]+)\s*stars?\)",
    ]
    for pat in patterns:
        m = re.search(pat, line)
        if m:
            return int(m.group(1).replace(",", ""))
    return None
