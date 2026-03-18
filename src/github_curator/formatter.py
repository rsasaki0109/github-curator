"""Output formatting for github-curator results."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from rich.table import Table

from github_curator.models import RepoInfo


def format_as_table(repos: list[RepoInfo]) -> Table:
    """Create a rich Table from a list of RepoInfo."""
    table = Table(title="GitHub Repositories", show_lines=False)
    table.add_column("Repository", style="cyan", no_wrap=True)
    table.add_column("Stars", justify="right", style="yellow")
    table.add_column("Forks", justify="right", style="green")
    table.add_column("Language", style="magenta")
    table.add_column("Last Updated", style="blue")
    table.add_column("Status", style="red")

    for repo in repos:
        updated = _format_date(repo.last_updated)
        status = "ARCHIVED" if repo.archived else ""
        table.add_row(
            repo.full_name,
            f"{repo.stars:,}",
            f"{repo.forks:,}",
            repo.language,
            updated,
            status,
        )

    return table


def format_as_markdown(repos: list[RepoInfo]) -> str:
    """Format repos as a markdown list with star badges."""
    lines = [f"# GitHub Repositories\n", f"_Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}_\n"]

    # Group by language
    by_lang: dict[str, list[RepoInfo]] = {}
    for repo in repos:
        lang = repo.language or "Other"
        by_lang.setdefault(lang, []).append(repo)

    for lang in sorted(by_lang):
        lines.append(f"\n## {lang}\n")
        for repo in sorted(by_lang[lang], key=lambda r: -r.stars):
            lines.append(repo.to_markdown())

    return "\n".join(lines) + "\n"


def format_as_json(repos: list[RepoInfo]) -> str:
    """Serialize repos to a JSON string.

    Output format is compatible with arxiv-curator for interoperability.
    """
    data = {
        "source": "github-curator",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(repos),
        "repositories": [repo.to_dict() for repo in repos],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _format_date(iso_date: str) -> str:
    """Convert ISO date string to a human-readable short format."""
    if not iso_date:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return iso_date
