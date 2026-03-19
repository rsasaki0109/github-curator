"""Tests for trend analysis."""

from datetime import datetime, timedelta, timezone

from github_curator.models import RepoInfo
from github_curator.trend import analyze_trend, analyze_trends


def _make_repo(**kwargs) -> RepoInfo:
    defaults = dict(owner="test", name="repo", stars=100)
    defaults.update(kwargs)
    return RepoInfo(**defaults)


class TestAnalyzeTrend:
    def test_growing_repo(self):
        """Active repo with many stars should be 'growing'."""
        repo = _make_repo(
            stars=100_000,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=3),
        )
        result = analyze_trend(repo)
        assert result.status == "growing"
        assert result.activity_score == 100
        assert result.monthly_star_rate >= 50
        assert "updated this week" in result.summary

    def test_archived_repo(self):
        """Archived repo should be 'inactive'."""
        repo = _make_repo(
            archived=True,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
        result = analyze_trend(repo)
        assert result.status == "inactive"
        assert result.activity_score == 0
        assert "ARCHIVED" in result.summary

    def test_stale_repo(self):
        """Repo not updated for >2 years should be 'inactive'."""
        repo = _make_repo(
            stars=500,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=800),
        )
        result = analyze_trend(repo)
        assert result.status == "inactive"
        assert result.activity_score == 10
        assert "inactive for" in result.summary

    def test_stable_repo(self):
        """Moderately active repo with modest stars should be 'stable'."""
        repo = _make_repo(
            stars=500,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=60),
        )
        result = analyze_trend(repo)
        assert result.status == "stable"
        assert result.activity_score == 60

    def test_no_push_data_repo(self):
        """Repo with no pushed_at and low stars should be 'inactive'."""
        repo = _make_repo(stars=10, pushed_at=None)
        result = analyze_trend(repo)
        # No pushed_at -> activity_score=0, not archived -> inactive
        assert result.status == "inactive"
        assert result.activity_score == 0

    def test_declining_repo(self):
        """Repo pushed 1-2 years ago should be 'declining'."""
        repo = _make_repo(
            stars=500,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=500),
        )
        result = analyze_trend(repo)
        assert result.status == "declining"
        assert result.activity_score == 20

    def test_stable_repo_recent_push_low_stars(self):
        """Recently pushed but low star rate should be 'stable'."""
        repo = _make_repo(
            stars=100,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=200),
        )
        result = analyze_trend(repo)
        assert result.status == "stable"
        assert result.activity_score == 30

    def test_summary_includes_stars(self):
        repo = _make_repo(stars=1234)
        result = analyze_trend(repo)
        assert "1,234 stars" in result.summary

    def test_summary_high_star_rate(self):
        """Repos with very high star rate should show stars/month."""
        repo = _make_repo(
            stars=500_000,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        result = analyze_trend(repo)
        assert "stars/month" in result.summary


class TestAnalyzeTrends:
    def test_sorts_by_activity_score(self):
        active = _make_repo(
            name="active",
            stars=100_000,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        stale = _make_repo(
            name="stale",
            stars=500,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=800),
        )
        moderate = _make_repo(
            name="moderate",
            stars=1000,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=60),
        )
        trends = analyze_trends([stale, active, moderate])
        assert trends[0].repo.name == "active"
        assert trends[1].repo.name == "moderate"
        assert trends[2].repo.name == "stale"

    def test_empty_list(self):
        assert analyze_trends([]) == []
