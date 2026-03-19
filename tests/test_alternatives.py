"""Tests for alternatives module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from github_curator.alternatives import Alternative, find_alternatives
from github_curator.models import RepoInfo


def _make_repo(**kwargs) -> RepoInfo:
    defaults = dict(owner="test", name="repo", stars=100)
    defaults.update(kwargs)
    return RepoInfo(**defaults)


class TestFindAlternatives:
    def test_active_fork_suggested(self):
        """An active fork with >10% stars should be suggested."""
        now = datetime.now(timezone.utc)
        original = _make_repo(
            owner="old-org",
            name="project",
            stars=1000,
            is_fork=False,
            pushed_at=now - timedelta(days=900),
        )
        active_fork = _make_repo(
            owner="new-user",
            name="project",
            stars=500,
            is_fork=True,
            pushed_at=now - timedelta(days=10),
        )

        api = MagicMock()
        api.get_top_forks.return_value = [active_fork]

        alts = find_alternatives(original, api)

        assert len(alts) == 1
        assert alts[0].replacement.owner == "new-user"
        assert "Active fork" in alts[0].reason
        api.get_top_forks.assert_called_once_with("old-org/project", limit=5)

    def test_fork_with_low_stars_not_suggested(self):
        """A fork with <=10% of original stars should not be suggested."""
        now = datetime.now(timezone.utc)
        original = _make_repo(
            owner="org",
            name="project",
            stars=1000,
            is_fork=False,
            pushed_at=now - timedelta(days=900),
        )
        weak_fork = _make_repo(
            owner="user",
            name="project",
            stars=50,  # 5% of original
            is_fork=True,
            pushed_at=now - timedelta(days=10),
        )

        api = MagicMock()
        api.get_top_forks.return_value = [weak_fork]

        alts = find_alternatives(original, api)
        assert len(alts) == 0

    def test_fork_not_more_recent_not_suggested(self):
        """A fork that is not more recently pushed should not be suggested."""
        now = datetime.now(timezone.utc)
        original = _make_repo(
            owner="org",
            name="project",
            stars=1000,
            is_fork=False,
            pushed_at=now - timedelta(days=30),
        )
        stale_fork = _make_repo(
            owner="user",
            name="project",
            stars=500,
            is_fork=True,
            pushed_at=now - timedelta(days=60),
        )

        api = MagicMock()
        api.get_top_forks.return_value = [stale_fork]

        alts = find_alternatives(original, api)
        assert len(alts) == 0

    def test_parent_more_active_suggested(self):
        """If this repo is a fork and parent is more active, suggest parent."""
        now = datetime.now(timezone.utc)
        fork = _make_repo(
            owner="user",
            name="project",
            stars=200,
            is_fork=True,
            parent_full_name="original-org/project",
            pushed_at=now - timedelta(days=500),
        )
        parent = _make_repo(
            owner="original-org",
            name="project",
            stars=5000,
            is_fork=False,
            pushed_at=now - timedelta(days=10),
        )

        api = MagicMock()
        api.get_repo_info_by_fullname.return_value = parent
        # get_top_forks should not be called since this repo is a fork
        api.get_top_forks.side_effect = AssertionError("should not be called")

        alts = find_alternatives(fork, api)

        assert len(alts) == 1
        assert alts[0].replacement.owner == "original-org"
        assert "Original repo is more active" in alts[0].reason
        api.get_repo_info_by_fullname.assert_called_once_with("original-org/project")

    def test_no_alternatives_found(self):
        """A healthy original repo with no active forks returns empty list."""
        now = datetime.now(timezone.utc)
        repo = _make_repo(
            owner="org",
            name="project",
            stars=1000,
            is_fork=False,
            pushed_at=now - timedelta(days=30),
        )

        api = MagicMock()
        api.get_top_forks.return_value = []

        alts = find_alternatives(repo, api)
        assert alts == []

    def test_archived_repo_with_active_fork(self):
        """An archived repo with an active fork should suggest it."""
        now = datetime.now(timezone.utc)
        archived = _make_repo(
            owner="xdspacelab",
            name="openvslam",
            stars=3200,
            is_fork=False,
            archived=True,
            pushed_at=now - timedelta(days=1000),
        )
        successor = _make_repo(
            owner="stella-cv",
            name="stella_vslam",
            stars=800,
            is_fork=True,
            pushed_at=now - timedelta(days=30),
        )

        api = MagicMock()
        api.get_top_forks.return_value = [successor]

        alts = find_alternatives(archived, api)

        assert len(alts) == 1
        assert alts[0].replacement.full_name == "stella-cv/stella_vslam"

    def test_api_error_returns_empty(self):
        """API errors should be silently caught, returning empty list."""
        repo = _make_repo(
            owner="org",
            name="project",
            stars=100,
            is_fork=False,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=900),
        )

        api = MagicMock()
        api.get_top_forks.side_effect = Exception("API error")

        alts = find_alternatives(repo, api)
        assert alts == []

    def test_multiple_forks_sorted_by_stars(self):
        """Multiple active forks should be sorted by stars descending."""
        now = datetime.now(timezone.utc)
        original = _make_repo(
            owner="org",
            name="project",
            stars=1000,
            is_fork=False,
            pushed_at=now - timedelta(days=900),
        )
        fork_a = _make_repo(
            owner="user-a",
            name="project",
            stars=200,
            pushed_at=now - timedelta(days=5),
        )
        fork_b = _make_repo(
            owner="user-b",
            name="project",
            stars=500,
            pushed_at=now - timedelta(days=3),
        )

        api = MagicMock()
        api.get_top_forks.return_value = [fork_a, fork_b]

        alts = find_alternatives(original, api)

        assert len(alts) == 2
        assert alts[0].replacement.stars == 500  # fork_b first
        assert alts[1].replacement.stars == 200  # fork_a second
