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


@app.command()
def stats(
    file: Path = typer.Argument(..., help="Path to an awesome-list markdown file."),
) -> None:
    """Show summary statistics for all GitHub repos in a markdown file."""
    from collections import Counter

    from rich.table import Table

    from github_curator.github_api import GitHubAPI
    from github_curator.parser import parse_markdown_repos

    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(code=1)

    content = file.read_text(encoding="utf-8")
    repo_refs = parse_markdown_repos(content)

    if not repo_refs:
        console.print("[yellow]No GitHub repository URLs found.[/yellow]")
        raise typer.Exit()

    console.print(f"[bold]Fetching info for {len(repo_refs)} repositories ...[/bold]")

    repos = []
    with GitHubAPI() as api:
        for ref in repo_refs:
            try:
                info = api.get_repo_info(ref.owner, ref.name)
                repos.append(info)
                console.print(f"  [green]OK[/green] {ref.owner}/{ref.name}")
            except Exception as e:
                console.print(f"  [red]SKIP[/red] {ref.owner}/{ref.name}: {e}")

    if not repos:
        console.print("[yellow]No repository data retrieved.[/yellow]")
        raise typer.Exit()

    total_repos = len(repos)
    total_stars = sum(r.stars for r in repos)
    avg_stars = total_stars / total_repos
    most_starred = max(repos, key=lambda r: r.stars)

    # Summary table
    summary_table = Table(title="Repository Statistics", show_lines=True)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="yellow", justify="right")
    summary_table.add_row("Total repos", str(total_repos))
    summary_table.add_row("Total stars", f"{total_stars:,}")
    summary_table.add_row("Average stars", f"{avg_stars:,.1f}")
    summary_table.add_row("Most starred", f"{most_starred.full_name} ({most_starred.stars:,} ⭐)")
    console.print()
    console.print(summary_table)

    # Language distribution table
    lang_counter: Counter[str] = Counter()
    for r in repos:
        lang_counter[r.language or "Unknown"] += 1

    lang_table = Table(title="Language Distribution", show_lines=False)
    lang_table.add_column("Language", style="magenta")
    lang_table.add_column("Count", justify="right", style="yellow")
    lang_table.add_column("Percentage", justify="right", style="green")

    for lang, count in lang_counter.most_common():
        pct = count / total_repos * 100
        lang_table.add_row(lang, str(count), f"{pct:.1f}%")

    console.print()
    console.print(lang_table)


@app.command()
def health(
    file: Path = typer.Argument(..., help="Path to a markdown file to check repo health."),
    only_problems: bool = typer.Option(False, "--only-problems", help="Show only warning/critical repos."),
) -> None:
    """Check health status of all repos in a markdown file."""
    import sys

    from rich.table import Table

    from github_curator.github_api import GitHubAPI
    from github_curator.health import compute_health
    from github_curator.parser import parse_markdown_repos

    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(code=1)

    content = file.read_text(encoding="utf-8")
    repo_refs = parse_markdown_repos(content)

    if not repo_refs:
        console.print("[yellow]No GitHub repository URLs found.[/yellow]")
        raise typer.Exit()

    console.print(f"[bold]Checking health of {len(repo_refs)} repositories ...[/bold]")

    results: list[tuple] = []
    has_critical = False

    with GitHubAPI() as api:
        for ref in repo_refs:
            try:
                info = api.get_repo_info(ref.owner, ref.name)
                h = compute_health(info)
                if h["status"] == "critical":
                    has_critical = True
                if only_problems and h["status"] == "healthy":
                    continue
                results.append((info, h))
                console.print(f"  [green]OK[/green] {ref.owner}/{ref.name}")
            except Exception as e:
                console.print(f"  [red]SKIP[/red] {ref.owner}/{ref.name}: {e}")

    table = Table(title="Repository Health", show_lines=False)
    table.add_column("Repo", style="cyan", no_wrap=True)
    table.add_column("Stars", justify="right", style="yellow")
    table.add_column("Last Push", style="blue")
    table.add_column("Status")
    table.add_column("Issues")

    for info, h in results:
        pushed = info.pushed_at.strftime("%Y-%m-%d") if info.pushed_at else "N/A"
        status = h["status"]
        if status == "healthy":
            status_str = "[green]healthy[/green]"
        elif status == "warning":
            status_str = "[yellow]warning[/yellow]"
        else:
            status_str = "[red]critical[/red]"
        issues_str = ", ".join(h["issues"]) if h["issues"] else ""
        table.add_row(info.full_name, f"{info.stars:,}", pushed, status_str, issues_str)

    console.print()
    console.print(table)

    if has_critical:
        raise typer.Exit(code=1)


@app.command()
def diff(
    file: Path = typer.Argument(..., help="Path to a markdown file."),
    against: Optional[Path] = typer.Option(None, "--against", help="Path to another markdown file to compare against."),
    ref: Optional[str] = typer.Option(None, "--ref", help="Git ref to compare against (e.g. HEAD~1, commit hash)."),
) -> None:
    """Compare repos in a markdown file against another version."""
    import subprocess

    from github_curator.differ import diff_lists

    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(code=1)

    new_content = file.read_text(encoding="utf-8")

    if against:
        if not against.exists():
            console.print(f"[red]File not found: {against}[/red]")
            raise typer.Exit(code=1)
        old_content = against.read_text(encoding="utf-8")
    else:
        git_ref = ref or "HEAD~1"
        try:
            result = subprocess.run(
                ["git", "show", f"{git_ref}:{file}"],
                capture_output=True,
                text=True,
                check=True,
            )
            old_content = result.stdout
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to get {file} from {git_ref}: {e.stderr.strip()}[/red]")
            raise typer.Exit(code=1)

    dr = diff_lists(old_content, new_content)

    if dr.added:
        console.print(f"\n[green bold]Added ({len(dr.added)}):[/green bold]")
        for r in dr.added:
            console.print(f"  [green]+ {r.owner}/{r.name}[/green]")

    if dr.removed:
        console.print(f"\n[red bold]Removed ({len(dr.removed)}):[/red bold]")
        for r in dr.removed:
            console.print(f"  [red]- {r.owner}/{r.name}[/red]")

    if not dr.added and not dr.removed:
        console.print("[green]No differences found.[/green]")
    else:
        console.print(f"\n[dim]Common repos: {len(dr.common)}[/dim]")


@app.command()
def dedupe(
    file: Path = typer.Argument(..., help="Path to a markdown file to check for duplicates."),
) -> None:
    """Detect duplicate and related repositories (forks of same upstream)."""
    from github_curator.dedupe import find_duplicates
    from github_curator.github_api import GitHubAPI
    from github_curator.parser import parse_markdown_repos

    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(code=1)

    content = file.read_text(encoding="utf-8")
    repo_refs = parse_markdown_repos(content)

    if not repo_refs:
        console.print("[yellow]No GitHub repository URLs found.[/yellow]")
        raise typer.Exit()

    console.print(f"[bold]Fetching info for {len(repo_refs)} repositories ...[/bold]")

    repos = []
    with GitHubAPI() as api:
        for ref in repo_refs:
            try:
                info = api.get_repo_info(ref.owner, ref.name)
                repos.append(info)
                console.print(f"  [green]OK[/green] {ref.owner}/{ref.name}")
            except Exception as e:
                console.print(f"  [red]SKIP[/red] {ref.owner}/{ref.name}: {e}")

    groups = find_duplicates(repos)

    if not groups:
        console.print("\n[green]No duplicate or related repos found.[/green]")
        return

    console.print(f"\n[bold]Found {len(groups)} group(s) of related repos:[/bold]")
    for i, group in enumerate(groups, 1):
        console.print(f"\n[bold cyan]Group {i}:[/bold cyan]")
        best = max(group, key=lambda r: r.stars)
        for repo in sorted(group, key=lambda r: -r.stars):
            fork_tag = " [dim](fork)[/dim]" if repo.is_fork else ""
            rec = " [green]<-- recommended[/green]" if repo is best else ""
            console.print(f"  {repo.full_name} ({repo.stars:,} stars){fork_tag}{rec}")


if __name__ == "__main__":
    app()
