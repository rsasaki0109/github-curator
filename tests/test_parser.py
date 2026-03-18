"""Tests for the markdown parser."""

from github_curator.parser import extract_star_count, parse_markdown_repos


SAMPLE_MARKDOWN = """\
# Awesome Robotics

## Frameworks

- [ROS 2](https://github.com/ros2/ros2) - Robot Operating System 2
- [MoveIt](https://github.com/moveit/moveit2) - Motion planning framework

## Tools

- [colcon](https://github.com/colcon/colcon-core) - Build tool
- Check out https://github.com/gazebosim/gz-sim for simulation.

## Links to skip

- See [issues](https://github.com/ros2/ros2/issues) for bugs.
- Also see https://github.com/ros2/ros2/pull/123
"""


class TestParseMarkdownRepos:
    def test_extracts_repos(self):
        repos = parse_markdown_repos(SAMPLE_MARKDOWN)
        full_names = [(r.owner, r.name) for r in repos]
        assert ("ros2", "ros2") in full_names
        assert ("moveit", "moveit2") in full_names
        assert ("colcon", "colcon-core") in full_names
        assert ("gazebosim", "gz-sim") in full_names

    def test_deduplicates(self):
        repos = parse_markdown_repos(SAMPLE_MARKDOWN)
        # ros2/ros2 appears multiple times (in link and in issues URL)
        owners = [r.owner for r in repos]
        assert owners.count("ros2") == 1

    def test_skips_non_repo_paths(self):
        repos = parse_markdown_repos(SAMPLE_MARKDOWN)
        names = [r.name for r in repos]
        assert "issues" not in names
        assert "pull" not in names

    def test_empty_input(self):
        assert parse_markdown_repos("") == []
        assert parse_markdown_repos("No GitHub links here.") == []

    def test_url_construction(self):
        repos = parse_markdown_repos(SAMPLE_MARKDOWN)
        for r in repos:
            assert r.url == f"https://github.com/{r.owner}/{r.name}"


class TestExtractStarCount:
    def test_star_emoji(self):
        assert extract_star_count("⭐ 1234") == 1234

    def test_star_with_comma(self):
        assert extract_star_count("Stars: 12,345") == 12345

    def test_parenthetical(self):
        assert extract_star_count("Some repo (500 stars)") == 500

    def test_no_stars(self):
        assert extract_star_count("Just a plain line") is None
