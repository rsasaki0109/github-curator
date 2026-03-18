"""Tests for duplicate detection."""

from github_curator.dedupe import find_duplicates
from github_curator.models import RepoInfo


def _make_repo(owner, name, stars=100, is_fork=False, parent_full_name="") -> RepoInfo:
    return RepoInfo(
        owner=owner,
        name=name,
        stars=stars,
        is_fork=is_fork,
        parent_full_name=parent_full_name,
    )


class TestFindDuplicates:
    def test_no_duplicates(self):
        repos = [
            _make_repo("a", "repo1"),
            _make_repo("b", "repo2"),
        ]
        assert find_duplicates(repos) == []

    def test_fork_and_parent_in_list(self):
        repos = [
            _make_repo("original", "project", stars=500),
            _make_repo("forker", "project", stars=50, is_fork=True, parent_full_name="original/project"),
        ]
        groups = find_duplicates(repos)
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_multiple_forks_same_parent(self):
        repos = [
            _make_repo("fork1", "repo", stars=30, is_fork=True, parent_full_name="upstream/repo"),
            _make_repo("fork2", "repo", stars=20, is_fork=True, parent_full_name="upstream/repo"),
        ]
        groups = find_duplicates(repos)
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_single_fork_parent_not_in_list(self):
        repos = [
            _make_repo("forker", "project", stars=50, is_fork=True, parent_full_name="upstream/project"),
            _make_repo("other", "unrelated", stars=200),
        ]
        groups = find_duplicates(repos)
        assert len(groups) == 0

    def test_fork_parent_in_list_grouped(self):
        repos = [
            _make_repo("upstream", "repo", stars=1000),
            _make_repo("fork1", "repo", stars=50, is_fork=True, parent_full_name="upstream/repo"),
            _make_repo("fork2", "repo", stars=30, is_fork=True, parent_full_name="upstream/repo"),
        ]
        groups = find_duplicates(repos)
        assert len(groups) == 1
        assert len(groups[0]) == 3
