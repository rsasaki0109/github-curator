"""Tests for github_curator.formatter."""

import json

from github_curator.formatter import format_as_json, format_as_markdown, format_as_table
from github_curator.models import RepoInfo


def _sample_repos() -> list[RepoInfo]:
    return [
        RepoInfo(owner="alice", name="alpha", stars=100, forks=10, language="Python", description="A project"),
        RepoInfo(owner="bob", name="beta", stars=50, forks=5, language="Rust", description="Another project"),
    ]


def test_format_as_table():
    table = format_as_table(_sample_repos())
    assert table.title == "GitHub Repositories"
    assert table.row_count == 2


def test_format_as_markdown():
    md = format_as_markdown(_sample_repos())
    assert "# GitHub Repositories" in md
    assert "![Stars]" in md
    assert "alice/alpha" in md
    assert "bob/beta" in md
    # Should group by language
    assert "## Python" in md
    assert "## Rust" in md


def test_format_as_json_valid():
    output = format_as_json(_sample_repos())
    data = json.loads(output)
    assert data["source"] == "github-curator"
    assert data["count"] == 2
    assert len(data["repositories"]) == 2
    assert data["repositories"][0]["owner"] == "alice"
