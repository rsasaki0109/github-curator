"""Tests for trend analysis."""

import json
from datetime import datetime, timedelta, timezone

from github_curator.models import RepoInfo
from github_curator.trend import (
    _activity_bar,
    analyze_trend,
    analyze_trends,
    build_comparative_summary,
    build_sector_summary,
    trends_to_json,
)


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


class TestGrowthEstimationWithCreatedAt:
    def test_uses_created_at_for_age(self):
        """When created_at is provided, age_months should reflect actual age."""
        created = datetime.now(timezone.utc) - timedelta(days=180)
        repo = _make_repo(
            stars=1200,
            created_at=created,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        result = analyze_trend(repo)
        assert 5.5 <= result.age_months <= 6.5  # ~6 months
        assert 190 <= result.monthly_star_rate <= 220  # 1200 / 6

    def test_fallback_without_created_at(self):
        """Without created_at, assume 36 months."""
        repo = _make_repo(stars=3600, created_at=None)
        result = analyze_trend(repo)
        assert result.age_months == 36.0
        assert abs(result.monthly_star_rate - 100.0) < 1.0

    def test_very_young_repo(self):
        """Repo created less than a month ago."""
        created = datetime.now(timezone.utc) - timedelta(days=10)
        repo = _make_repo(
            stars=500,
            created_at=created,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        result = analyze_trend(repo)
        assert result.age_months >= 1  # clamped to minimum 1
        assert result.monthly_star_rate >= 400  # 500 / ~1


class TestActivityBreakdown:
    def test_open_issues_ratio(self):
        repo = _make_repo(stars=1000, open_issues_count=50)
        result = analyze_trend(repo)
        assert abs(result.open_issues_ratio - 0.05) < 0.001

    def test_fork_ratio(self):
        repo = _make_repo(stars=1000, forks=200)
        result = analyze_trend(repo)
        assert abs(result.fork_ratio - 0.2) < 0.001

    def test_zero_stars_no_division_error(self):
        repo = _make_repo(stars=0, forks=5, open_issues_count=3)
        result = analyze_trend(repo)
        # Should use max(stars, 1) to avoid division by zero
        assert result.open_issues_ratio == 3.0
        assert result.fork_ratio == 5.0

    def test_days_since_push(self):
        pushed = datetime.now(timezone.utc) - timedelta(days=42)
        repo = _make_repo(pushed_at=pushed)
        result = analyze_trend(repo)
        assert result.days_since_push == 42

    def test_days_since_push_none(self):
        repo = _make_repo(pushed_at=None)
        result = analyze_trend(repo)
        assert result.days_since_push is None


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


class TestComparativeAnalysis:
    def test_basic_insights(self):
        repos = [
            _make_repo(
                owner="a", name="fast",
                stars=10_000,
                created_at=datetime.now(timezone.utc) - timedelta(days=60),
                pushed_at=datetime.now(timezone.utc) - timedelta(days=1),
            ),
            _make_repo(
                owner="b", name="big",
                stars=50_000,
                created_at=datetime.now(timezone.utc) - timedelta(days=1800),
                pushed_at=datetime.now(timezone.utc) - timedelta(days=30),
            ),
            _make_repo(
                owner="c", name="old",
                stars=500,
                created_at=datetime.now(timezone.utc) - timedelta(days=1800),
                pushed_at=datetime.now(timezone.utc) - timedelta(days=400),
            ),
        ]
        trends = analyze_trends(repos)
        insights = build_comparative_summary(trends)

        assert any("Fastest growing" in i for i in insights)
        assert any("Most active" in i for i in insights)
        assert any("Largest" in i for i in insights)
        # "fast" is fastest growing (10000 / 2 months = 5000/mo)
        assert any("a/fast" in i for i in insights)
        # "big" is largest
        assert any("b/big" in i and "50,000" in i for i in insights)

    def test_rising_star(self):
        repos = [
            _make_repo(
                owner="x", name="rising",
                stars=500,
                created_at=datetime.now(timezone.utc) - timedelta(days=90),
                pushed_at=datetime.now(timezone.utc) - timedelta(days=2),
            ),
            _make_repo(
                owner="y", name="veteran",
                stars=10_000,
                created_at=datetime.now(timezone.utc) - timedelta(days=1800),
                pushed_at=datetime.now(timezone.utc) - timedelta(days=10),
            ),
        ]
        trends = analyze_trends(repos)
        insights = build_comparative_summary(trends)
        assert any("Rising star" in i and "x/rising" in i for i in insights)

    def test_no_rising_star_when_all_old(self):
        repos = [
            _make_repo(
                owner="a", name="old1",
                stars=1000,
                created_at=datetime.now(timezone.utc) - timedelta(days=500),
                pushed_at=datetime.now(timezone.utc) - timedelta(days=10),
            ),
        ]
        trends = analyze_trends(repos)
        insights = build_comparative_summary(trends)
        assert not any("Rising star" in i for i in insights)

    def test_empty(self):
        assert build_comparative_summary([]) == []


class TestSectorSummary:
    def test_sector_with_topic(self):
        repos = [
            _make_repo(
                owner="a", name="r1", stars=1000,
                pushed_at=datetime.now(timezone.utc) - timedelta(days=5),
            ),
            _make_repo(
                owner="b", name="r2", stars=3000,
                pushed_at=datetime.now(timezone.utc) - timedelta(days=50),
            ),
            _make_repo(
                owner="c", name="r3", stars=500,
                pushed_at=datetime.now(timezone.utc) - timedelta(days=800),
            ),
        ]
        trends = analyze_trends(repos)
        sector = build_sector_summary(trends, "slam")
        assert any("slam" in s for s in sector)
        assert any("average stars" in s.lower() for s in sector)
        assert any("Growing" in s for s in sector)

    def test_empty_sector(self):
        assert build_sector_summary([], "test") == []


class TestActivityBar:
    def test_full_bar(self):
        bar = _activity_bar(100)
        assert bar == "\u2588" * 10

    def test_empty_bar(self):
        bar = _activity_bar(0)
        assert bar == "\u2591" * 10

    def test_partial_bar(self):
        bar = _activity_bar(50)
        assert len(bar) == 10
        assert bar.count("\u2588") == 5
        assert bar.count("\u2591") == 5

    def test_custom_width(self):
        bar = _activity_bar(80, width=5)
        assert len(bar) == 5
        assert bar.count("\u2588") == 4


class TestJsonOutput:
    def test_trends_to_json(self):
        repos = [
            _make_repo(
                owner="a", name="repo1", stars=1000, forks=100,
                open_issues_count=10,
                created_at=datetime.now(timezone.utc) - timedelta(days=365),
                pushed_at=datetime.now(timezone.utc) - timedelta(days=5),
            ),
        ]
        trends = analyze_trends(repos)
        result = trends_to_json(trends)
        data = json.loads(result)
        assert "repos" in data
        assert "comparative" in data
        assert len(data["repos"]) == 1
        repo_data = data["repos"][0]
        assert repo_data["repo"] == "a/repo1"
        assert repo_data["stars"] == 1000
        assert "status" in repo_data
        assert "monthly_star_rate" in repo_data
        assert "age_months" in repo_data
        assert "open_issues_ratio" in repo_data
        assert "fork_ratio" in repo_data

    def test_trends_to_json_with_topic(self):
        repos = [
            _make_repo(
                owner="a", name="r1", stars=500,
                pushed_at=datetime.now(timezone.utc) - timedelta(days=5),
            ),
        ]
        trends = analyze_trends(repos)
        result = trends_to_json(trends, topic="robotics")
        data = json.loads(result)
        assert "sector" in data
        assert any("robotics" in s for s in data["sector"])

    def test_trends_to_json_without_topic(self):
        repos = [
            _make_repo(
                owner="a", name="r1", stars=500,
                pushed_at=datetime.now(timezone.utc) - timedelta(days=5),
            ),
        ]
        trends = analyze_trends(repos)
        result = trends_to_json(trends)
        data = json.loads(result)
        assert "sector" not in data

    def test_to_dict(self):
        repo = _make_repo(
            stars=1000, forks=200, open_issues_count=30,
            created_at=datetime.now(timezone.utc) - timedelta(days=180),
            pushed_at=datetime.now(timezone.utc) - timedelta(days=3),
        )
        trend = analyze_trend(repo)
        d = trend.to_dict()
        assert d["repo"] == "test/repo"
        assert d["stars"] == 1000
        assert d["forks"] == 200
        assert isinstance(d["monthly_star_rate"], float)
        assert isinstance(d["age_months"], float)
        assert isinstance(d["open_issues_ratio"], float)
        assert isinstance(d["fork_ratio"], float)
