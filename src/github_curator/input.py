"""Unified input resolution for github-curator commands."""

from __future__ import annotations

from pathlib import Path

from github_curator.parser import RepoRef, parse_markdown_repos


def resolve_repos(
    urls: list[str] | None = None,
    file: Path | None = None,
    topic: str | None = None,
    max_results: int = 50,
) -> list[RepoRef]:
    """Resolve repo references from any combination of input methods.

    Args:
        urls: Direct GitHub repository URLs.
        file: Path to a Markdown or plain-text file containing GitHub URLs.
        topic: GitHub topic to search for repositories.
        max_results: Maximum number of repos to return when using topic search.

    Returns:
        Deduplicated list of RepoRef.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If no input method is provided.
    """
    refs: list[RepoRef] = []

    if urls:
        # Reuse parser.py's regex for consistency
        pseudo_md = "\n".join(f"- [{url}]({url})" for url in urls)
        refs.extend(parse_markdown_repos(pseudo_md))

    if file is not None:
        if not file.exists():
            raise FileNotFoundError(f"File not found: {file}")
        content = file.read_text(encoding="utf-8")
        refs.extend(parse_markdown_repos(content))

    if topic:
        from github_curator.github_api import GitHubAPI

        with GitHubAPI() as api:
            results = api.search_repos_by_topic(topic, max_results=max_results)
            refs.extend(results)

    # Deduplicate by (owner, name)
    seen: set[tuple[str, str]] = set()
    unique: list[RepoRef] = []
    for ref in refs:
        key = (ref.owner.lower(), ref.name.lower())
        if key not in seen:
            seen.add(key)
            unique.append(ref)

    return unique
