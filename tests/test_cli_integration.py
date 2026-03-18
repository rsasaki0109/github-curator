"""CLI integration tests using typer.testing.CliRunner."""

from typer.testing import CliRunner

from github_curator.cli import app

runner = CliRunner()


def test_health_nonexistent_file():
    result = runner.invoke(app, ["health", "nonexistent.md"])
    assert result.exit_code != 0
    assert "File not found" in result.output


def test_diff_nonexistent_file():
    result = runner.invoke(app, ["diff", "nonexistent.md"])
    assert result.exit_code != 0
    assert "File not found" in result.output


def test_check_links_empty_markdown(tmp_path):
    md = tmp_path / "empty.md"
    md.write_text("# No repos here\n", encoding="utf-8")
    result = runner.invoke(app, ["check-links", str(md)])
    assert result.exit_code == 0
    assert "No GitHub repository URLs found" in result.output


def test_stats_no_github_urls(tmp_path):
    md = tmp_path / "no_urls.md"
    md.write_text("# Just text\nNo links at all.\n", encoding="utf-8")
    result = runner.invoke(app, ["stats", str(md)])
    assert result.exit_code == 0
    assert "No GitHub repository URLs found" in result.output


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "github-curator" in result.output


def test_help_flag():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "GitHub repository tracking" in result.output
