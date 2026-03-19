"""Tests for alternatives module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from github_curator.alternatives import (
    Alternative,
    _compute_confidence,
    extract_keywords,
    find_alternatives,
)
from github_curator.models import RepoInfo


def _make_repo(**kwargs) -> RepoInfo:
    defaults = dict(owner="test", name="repo", stars=100)
    defaults.update(kwargs)
    return RepoInfo(**defaults)


class TestExtractKeywords:
    def test_basic_extraction(self):
        keywords = extract_keywords("owner/visual-slam-lib", "A visual SLAM library for robotics")
        assert "visual" in keywords
        assert "slam" in keywords
        assert "lib" in keywords
        assert "robotics" in keywords

    def test_stop_words_removed(self):
        keywords = extract_keywords("owner/repo", "A library for the best things in the world")
        assert "a" not in keywords
        assert "for" not in keywords
        assert "the" not in keywords
        assert "in" not in keywords

    def test_short_tokens_removed(self):
        keywords = extract_keywords("owner/a-b-cd", "x y ab")
        assert "a" not in keywords
        assert "b" not in keywords
        assert "x" not in keywords
        assert "y" not in keywords
        assert "cd" in keywords
        assert "ab" in keywords

    def test_deduplication(self):
        keywords = extract_keywords("owner/slam", "SLAM based slam system")
        assert keywords.count("slam") == 1

    def test_empty_description(self):
        keywords = extract_keywords("owner/cool-project", "")
        assert "cool" in keywords
        assert "project" in keywords

    def test_owner_not_included(self):
        keywords = extract_keywords("mycompany/tool", "A useful tool")
        assert "mycompany" not in keywords


class TestComputeConfidence:
    def test_fork_more_stars_is_high(self):
        original = _make_repo(stars=100)
        replacement = _make_repo(stars=200)
        assert _compute_confidence(original, replacement, "fork") == "high"

    def test_fork_less_stars_is_medium(self):
        original = _make_repo(stars=1000)
        replacement = _make_repo(stars=200)
        assert _compute_confidence(original, replacement, "fork") == "medium"

    def test_fork_equal_stars_is_high(self):
        original = _make_repo(stars=100)
        replacement = _make_repo(stars=100)
        assert _compute_confidence(original, replacement, "fork") == "high"

    def test_parent_is_always_high(self):
        original = _make_repo(stars=100)
        replacement = _make_repo(stars=50)
        assert _compute_confidence(original, replacement, "parent") == "high"

    def test_search_is_always_low(self):
        original = _make_repo(stars=100)
        replacement = _make_repo(stars=10000)
        assert _compute_confidence(original, replacement, "search") == "low"


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
        api.search_similar_repos.return_value = []

        alts = find_alternatives(original, api)

        assert len(alts) == 1
        assert alts[0].replacement.owner == "new-user"
        assert "Active fork" in alts[0].reason
        assert alts[0].confidence == "medium"
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
        api.search_similar_repos.return_value = []

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
        api.search_similar_repos.return_value = []

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
        api.search_similar_repos.return_value = []

        alts = find_alternatives(fork, api)

        assert len(alts) == 1
        assert alts[0].replacement.owner == "original-org"
        assert "Original repo is more active" in alts[0].reason
        assert alts[0].confidence == "high"
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
        api.search_similar_repos.return_value = []

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
        api.search_similar_repos.return_value = []

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
        api.search_similar_repos.side_effect = Exception("API error")

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
        api.search_similar_repos.return_value = []

        alts = find_alternatives(original, api)

        assert len(alts) == 2
        assert alts[0].replacement.stars == 500  # fork_b first
        assert alts[1].replacement.stars == 200  # fork_a second

    def test_similar_repo_suggested(self):
        """Strategy 3: similar repos from keyword search should be suggested."""
        now = datetime.now(timezone.utc)
        original = _make_repo(
            owner="old-org",
            name="visual-slam",
            stars=500,
            is_fork=False,
            language="C++",
            description="A visual SLAM library",
            pushed_at=now - timedelta(days=900),
        )
        similar = _make_repo(
            owner="new-org",
            name="better-slam",
            stars=1200,
            language="C++",
            pushed_at=now - timedelta(days=10),
        )

        api = MagicMock()
        api.get_top_forks.return_value = []
        api.search_similar_repos.return_value = [similar]

        alts = find_alternatives(original, api)

        assert len(alts) == 1
        assert alts[0].replacement.full_name == "new-org/better-slam"
        assert alts[0].confidence == "low"
        assert "Similar repo" in alts[0].reason

    def test_similar_repo_skipped_if_archived(self):
        """Archived similar repos should not be suggested."""
        now = datetime.now(timezone.utc)
        original = _make_repo(
            owner="org",
            name="project",
            stars=500,
            is_fork=False,
            pushed_at=now - timedelta(days=900),
        )
        archived_similar = _make_repo(
            owner="other",
            name="similar",
            stars=1000,
            archived=True,
            pushed_at=now - timedelta(days=10),
        )

        api = MagicMock()
        api.get_top_forks.return_value = []
        api.search_similar_repos.return_value = [archived_similar]

        alts = find_alternatives(original, api)
        assert len(alts) == 0

    def test_similar_repo_skipped_if_no_improvement(self):
        """Similar repos with fewer stars and older push should not be suggested."""
        now = datetime.now(timezone.utc)
        original = _make_repo(
            owner="org",
            name="project",
            stars=5000,
            is_fork=False,
            pushed_at=now - timedelta(days=30),
        )
        worse = _make_repo(
            owner="other",
            name="similar",
            stars=100,
            pushed_at=now - timedelta(days=60),
        )

        api = MagicMock()
        api.get_top_forks.return_value = []
        api.search_similar_repos.return_value = [worse]

        alts = find_alternatives(original, api)
        assert len(alts) == 0

    def test_duplicate_between_fork_and_search_skipped(self):
        """A repo found as both fork and search result should appear only once."""
        now = datetime.now(timezone.utc)
        original = _make_repo(
            owner="org",
            name="project",
            stars=1000,
            is_fork=False,
            pushed_at=now - timedelta(days=900),
        )
        fork = _make_repo(
            owner="user",
            name="project",
            stars=500,
            is_fork=True,
            pushed_at=now - timedelta(days=5),
        )

        api = MagicMock()
        api.get_top_forks.return_value = [fork]
        # Same repo returned by search
        api.search_similar_repos.return_value = [fork]

        alts = find_alternatives(original, api)
        full_names = [a.replacement.full_name for a in alts]
        assert full_names.count("user/project") == 1

    def test_confidence_on_fork_with_more_stars(self):
        """A fork with more stars than original should have high confidence."""
        now = datetime.now(timezone.utc)
        original = _make_repo(
            owner="org",
            name="project",
            stars=100,
            is_fork=False,
            pushed_at=now - timedelta(days=900),
        )
        popular_fork = _make_repo(
            owner="user",
            name="project",
            stars=500,
            is_fork=True,
            pushed_at=now - timedelta(days=5),
        )

        api = MagicMock()
        api.get_top_forks.return_value = [popular_fork]
        api.search_similar_repos.return_value = []

        alts = find_alternatives(original, api)
        assert len(alts) == 1
        assert alts[0].confidence == "high"
