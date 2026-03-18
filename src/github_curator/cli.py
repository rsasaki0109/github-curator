"""CLI entry point for github-curator."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from github_curator import __version__

app = typer.Typer(
    name="github-curator",
    help="GitHub repository tracking and curation CLI tool.",
    add_completion=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"github-curator {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """GitHub repository tracking and curation CLI tool."""


@app.command()
def update_stars(
    file: Path = typer.Argument(..., help="Path to an awesome-list markdown file."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show changes without writing."),
) -> None:
    """Update GitHub star counts for all repos in a markdown file."""
    from github_curator.github_api import GitHubAPI
    from github_curator.updater import update_awesome_stars

    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[bold]Updating stars in [cyan]{file}[/cyan] ...[/bold]")

    with GitHubAPI() as api:
        rl = api.get_rate_limit_info()
        console.print(f"  API rate limit remaining: {rl['remaining']}/{rl['limit']}")

        diffs = update_awesome_stars(file, api=api, dry_run=dry_run)

    if not diffs:
        console.print("[green]No changes detected.[/green]")
        return

    console.print(f"\n[bold]Changes ({len(diffs)}):[/bold]")
    for d in diffs:
        sign = "+" if d.diff > 0 else ""
        color = "green" if d.diff > 0 else ("red" if d.diff < 0 else "yellow")
        console.print(f"  [{color}]{d.repo.full_name}: {d.old_stars:,} -> {d.new_stars:,} ({sign}{d.diff:,})[/{color}]")

    if dry_run:
        console.print("\n[yellow]Dry run — no files were modified.[/yellow]")
    else:
        console.print(f"\n[green]Updated {file}[/green]")


@app.command()
def trending(
    query: str = typer.Argument("stars:>1000", help="Search query (e.g. 'topic:robotics language:python')."),
    sort: str = typer.Option("stars", "--sort", "-s", help="Sort by: stars, forks, updated."),
    max_results: int = typer.Option(25, "--max", "-m", help="Maximum number of results."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: table (default), markdown, json."),
) -> None:
    """Search trending repositories on GitHub."""
    from github_curator.formatter import format_as_json, format_as_markdown, format_as_table
    from github_curator.github_api import GitHubAPI

    console.print(f"[bold]Searching: [cyan]{query}[/cyan] (sort={sort}, max={max_results})[/bold]")

    with GitHubAPI() as api:
        repos = api.search_repos(query=query, sort_by=sort, max_results=max_results)

    if not repos:
        console.print("[yellow]No results found.[/yellow]")
        raise typer.Exit()

    fmt = (output or "table").lower()
    if fmt == "json":
        console.print(format_as_json(repos))
    elif fmt == "markdown":
        console.print(format_as_markdown(repos))
    else:
        console.print(format_as_table(repos))


@app.command()
def check_links(
    file: Path = typer.Argument(..., help="Path to a markdown file to check."),
) -> None:
    """Verify all GitHub links in a markdown file are still alive."""
    from github_curator.github_api import GitHubAPI
    from github_curator.parser import parse_markdown_repos

    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(code=1)

    content = file.read_text(encoding="utf-8")
    repos = parse_markdown_repos(content)

    if not repos:
        console.print("[yellow]No GitHub repository URLs found.[/yellow]")
        raise typer.Exit()

    console.print(f"[bold]Checking {len(repos)} repositories ...[/bold]")
    broken: list[tuple[str, str]] = []

    with GitHubAPI() as api:
        for ref in repos:
            exists, error = api.check_repo_exists(ref.owner, ref.name)
            if exists:
                console.print(f"  [green]OK[/green]  {ref.owner}/{ref.name}")
            else:
                console.print(f"  [red]FAIL[/red] {ref.owner}/{ref.name} — {error}")
                broken.append((f"{ref.owner}/{ref.name}", error or "Unknown"))

    console.print()
    if broken:
        console.print(f"[red bold]{len(broken)} broken link(s) found:[/red bold]")
        for name, err in broken:
            console.print(f"  [red]- {name}: {err}[/red]")
        raise typer.Exit(code=1)
    else:
        console.print(f"[green bold]All {len(repos)} links are valid.[/green bold]")


@app.command()
def export(
    file: Path = typer.Argument(..., help="Path to a markdown file to export repos from."),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json, markdown."),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Write to file instead of stdout."),
) -> None:
    """Export repository data from a markdown file to JSON or markdown."""
    from github_curator.formatter import format_as_json, format_as_markdown
    from github_curator.github_api import GitHubAPI
    from github_curator.parser import parse_markdown_repos

    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(code=1)

    content = file.read_text(encoding="utf-8")
    repos_refs = parse_markdown_repos(content)

    if not repos_refs:
        console.print("[yellow]No GitHub repository URLs found.[/yellow]")
        raise typer.Exit()

    console.print(f"[bold]Fetching info for {len(repos_refs)} repositories ...[/bold]")

    repos = []
    with GitHubAPI() as api:
        for ref in repos_refs:
            try:
                info = api.get_repo_info(ref.owner, ref.name)
                repos.append(info)
                console.print(f"  [green]OK[/green] {ref.owner}/{ref.name}")
            except Exception as e:
                console.print(f"  [red]SKIP[/red] {ref.owner}/{ref.name}: {e}")

    fmt = format.lower()
    if fmt == "markdown":
        result = format_as_markdown(repos)
    else:
        result = format_as_json(repos)

    if output_file:
        output_file.write_text(result, encoding="utf-8")
        console.print(f"\n[green]Exported {len(repos)} repos to {output_file}[/green]")
    else:
        console.print()
        console.print(result)


if __name__ == "__main__":
    app()
