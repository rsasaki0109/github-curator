"""CLI integration tests using typer.testing.CliRunner."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from github_curator.cli import app

runner = CliRunner()


def test_health_no_input():
    """health with no input should show an error."""
    result = runner.invoke(app, ["health"])
    assert result.exit_code != 0
    assert "Provide at least one input method" in result.output


def test_health_nonexistent_file():
    result = runner.invoke(app, ["health", "--file", "nonexistent.md"])
    assert result.exit_code != 0
    assert "File not found" in result.output


def _make_mock_api():
    mock_api = MagicMock()
    mock_info = MagicMock()
    mock_info.full_name = "octocat/Hello-World"
    mock_info.stars = 100
    mock_info.pushed_at = None
    mock_api.get_repo_info.return_value = mock_info
    return mock_api, mock_info


def test_health_with_file(tmp_path):
    md = tmp_path / "repos.md"
    md.write_text(
        "- [repo](https://github.com/octocat/Hello-World) - desc\n",
        encoding="utf-8",
    )
    mock_api, _ = _make_mock_api()

    with patch("github_curator.github_api.GitHubAPI") as mock_cls:
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_api)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        with patch("github_curator.health.compute_health") as mock_health:
            mock_health.return_value = {"status": "healthy", "issues": []}
            result = runner.invoke(app, ["health", "--file", str(md)])

    assert "Found" in result.output
    assert "1" in result.output


def test_health_with_urls():
    mock_api, _ = _make_mock_api()

    with patch("github_curator.github_api.GitHubAPI") as mock_cls:
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_api)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        with patch("github_curator.health.compute_health") as mock_health:
            mock_health.return_value = {"status": "healthy", "issues": []}
            result = runner.invoke(
                app,
                ["health", "https://github.com/octocat/Hello-World"],
            )

    assert "Found" in result.output


def test_diff_nonexistent_file():
    result = runner.invoke(app, ["diff", "nonexistent.md"])
    assert result.exit_code != 0
    assert "File not found" in result.output


def test_check_links_no_input():
    result = runner.invoke(app, ["check-links"])
    assert result.exit_code != 0
    assert "Provide at least one input method" in result.output


def test_check_links_empty_markdown(tmp_path):
    md = tmp_path / "empty.md"
    md.write_text("# No repos here\n", encoding="utf-8")
    result = runner.invoke(app, ["check-links", "--file", str(md)])
    assert result.exit_code == 0
    assert "No GitHub repositories found" in result.output


def test_stats_no_input():
    result = runner.invoke(app, ["stats"])
    assert result.exit_code != 0
    assert "Provide at least one input method" in result.output


def test_stats_empty_file(tmp_path):
    md = tmp_path / "no_urls.md"
    md.write_text("# Just text\nNo links at all.\n", encoding="utf-8")
    result = runner.invoke(app, ["stats", "--file", str(md)])
    assert result.exit_code == 0
    assert "No GitHub repositories found" in result.output


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "github-curator" in result.output


def test_help_flag():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "GitHub repository tracking" in result.output
