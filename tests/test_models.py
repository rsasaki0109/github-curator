"""Tests for github_curator.models."""

import json
from datetime import datetime, timezone

from github_curator.models import RepoInfo, StarDiff


def _sample_repo() -> RepoInfo:
    return RepoInfo(
        owner="alice",
        name="alpha",
        stars=100,
        forks=10,
        description="A sample project",
        language="Python",
    )


def test_repo_info_to_dict():
    repo = _sample_repo()
    d = repo.to_dict()
    assert d["owner"] == "alice"
    assert d["name"] == "alpha"
    assert d["stars"] == 100
    assert d["type"] == "github_repo"
    assert d["full_name"] == "alice/alpha"


def test_repo_info_to_markdown():
    repo = _sample_repo()
    md = repo.to_markdown()
    assert "alice/alpha" in md
    assert "![Stars]" in md
    assert "`Python`" in md
    assert "A sample project" in md
    assert md.startswith("- [")


def test_repo_info_to_json_valid():
    repo = _sample_repo()
    output = repo.to_json()
    data = json.loads(output)
    assert data["owner"] == "alice"
    assert data["stars"] == 100
    assert data["type"] == "github_repo"


def test_repo_info_to_dict_with_pushed_at():
    """Verify that pushed_at datetime is serialized to ISO string in to_dict/to_json."""
    dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    repo = RepoInfo(owner="alice", name="alpha", stars=100, pushed_at=dt)
    d = repo.to_dict()
    assert d["pushed_at"] == "2024-06-15T12:00:00+00:00"
    # Verify JSON round-trip works
    output = repo.to_json()
    data = json.loads(output)
    assert data["pushed_at"] == "2024-06-15T12:00:00+00:00"


def test_repo_info_to_dict_pushed_at_none():
    repo = RepoInfo(owner="alice", name="alpha", stars=100)
    d = repo.to_dict()
    assert d["pushed_at"] is None


def test_repo_info_from_dict_with_pushed_at():
    """Verify that pushed_at string is converted back to datetime in from_dict."""
    data = {
        "owner": "alice",
        "name": "alpha",
        "stars": 100,
        "pushed_at": "2024-06-15T12:00:00+00:00",
    }
    repo = RepoInfo.from_dict(data)
    assert isinstance(repo.pushed_at, datetime)
    assert repo.pushed_at.year == 2024


def test_star_diff():
    repo = _sample_repo()
    diff = StarDiff(repo=repo, old_stars=80, new_stars=100)
    assert diff.diff == 20
    assert diff.changed is True
    assert "+20" in str(diff)

    no_change = StarDiff(repo=repo, old_stars=100, new_stars=100)
    assert no_change.diff == 0
    assert no_change.changed is False
