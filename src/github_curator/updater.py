"""Update star counts in awesome-list markdown files."""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console

from github_curator.github_api import GitHubAPI
from github_curator.models import RepoInfo, StarDiff
from github_curator.parser import RepoRef, extract_star_count, parse_markdown_repos

# Badge pattern: ![Stars](https://img.shields.io/github/stars/owner/repo)
_BADGE_RE = re.compile(
    r"!\[Stars\]\(https://img\.shields\.io/github/stars/[^)]+\)"
)

# Inline star count patterns
_STAR_INLINE_RE = re.compile(r"[⭐★]\s*[\d,]+")


def update_awesome_stars(
    markdown_file_path: str | Path,
    api: GitHubAPI | None = None,
    dry_run: bool = False,
    console: Console | None = None,
) -> list[StarDiff]:
    """Read a markdown file, fetch star counts, and update badges in-place.

    Args:
        markdown_file_path: Path to the markdown file.
        api: Optional GitHubAPI instance (creates one if not provided).
        dry_run: If True, do not write changes to disk.
        console: Optional Console for output. Creates one if not provided.

    Returns:
        List of StarDiff objects showing what changed.
    """
    if console is None:
        console = Console()
    path = Path(markdown_file_path)
    content = path.read_text(encoding="utf-8")
    repos = parse_markdown_repos(content)

    if not repos:
        console.print("[yellow]No GitHub repository URLs found in the file.[/yellow]")
        return []

    own_api = api is None
    if own_api:
        api = GitHubAPI()

    diffs: list[StarDiff] = []
    lines = content.splitlines()

    try:
        for repo_ref in repos:
            console.print(f"  Fetching [cyan]{repo_ref.owner}/{repo_ref.name}[/cyan] ...")
            try:
                info = api.get_repo_info(repo_ref.owner, repo_ref.name)
            except Exception as e:
                console.print(f"  [red]Error fetching {repo_ref.owner}/{repo_ref.name}: {e}[/red]")
                continue

            # Update lines that reference this repo
            for i, line in enumerate(lines):
                if f"github.com/{repo_ref.owner}/{repo_ref.name}" not in line:
                    continue

                old_stars = extract_star_count(line) or 0
                new_line = _update_line_stars(line, repo_ref, info)

                if new_line != line:
                    lines[i] = new_line
                    diffs.append(StarDiff(repo=info, old_stars=old_stars, new_stars=info.stars))

    finally:
        if own_api:
            api.close()

    if not dry_run and diffs:
        updated_content = "\n".join(lines)
        # Preserve trailing newline
        if content.endswith("\n"):
            updated_content += "\n"
        path.write_text(updated_content, encoding="utf-8")

    return diffs


def _update_line_stars(line: str, ref: RepoRef, info: RepoInfo) -> str:
    """Update star information in a single markdown line."""
    badge = f"![Stars](https://img.shields.io/github/stars/{ref.owner}/{ref.name})"

    # If there's already a badge, replace it
    if _BADGE_RE.search(line):
        line = _BADGE_RE.sub(badge, line)
    # If there's an inline star count, update it
    elif _STAR_INLINE_RE.search(line):
        line = _STAR_INLINE_RE.sub(f"\u2b50 {info.stars:,}", line)
    else:
        # Append badge after the repo link
        repo_url = f"https://github.com/{ref.owner}/{ref.name}"
        # Handle markdown link: [text](url)
        md_link_pattern = re.compile(
            r"(\[[^\]]*\]\(" + re.escape(repo_url) + r"\))"
        )
        m = md_link_pattern.search(line)
        if m:
            line = line[: m.end()] + " " + badge + line[m.end() :]
        else:
            # Just append after the plain URL
            idx = line.find(repo_url)
            if idx >= 0:
                end = idx + len(repo_url)
                line = line[:end] + " " + badge + line[end:]

    return line
