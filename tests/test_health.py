"""Tests for health assessment."""

from datetime import datetime, timedelta, timezone

from github_curator.health import compute_health
from github_curator.models import RepoInfo


def _make_repo(**kwargs) -> RepoInfo:
    defaults = dict(owner="test", name="repo", stars=100)
    defaults.update(kwargs)
    return RepoInfo(**defaults)


class TestComputeHealth:
    def test_healthy_repo(self):
        repo = _make_repo(
            pushed_at=datetime.now(timezone.utc) - timedelta(days=30),
            open_issues_count=10,
            license_name="MIT",
        )
        result = compute_health(repo)
        assert result["status"] == "healthy"
        assert result["issues"] == []

    def test_archived_is_critical(self):
        repo = _make_repo(archived=True, license_name="MIT")
        result = compute_health(repo)
        assert result["status"] == "critical"
        assert "Archived" in result["issues"]

    def test_no_updates_two_years_is_critical(self):
        repo = _make_repo(
            pushed_at=datetime.now(timezone.utc) - timedelta(days=800),
            license_name="MIT",
        )
        result = compute_health(repo)
        assert result["status"] == "critical"
        assert "No updates for >2 years" in result["issues"]

    def test_no_updates_one_year_is_warning(self):
        repo = _make_repo(
            pushed_at=datetime.now(timezone.utc) - timedelta(days=400),
            license_name="MIT",
        )
        result = compute_health(repo)
        assert result["status"] == "warning"
        assert "No updates for >1 year" in result["issues"]

    def test_high_issue_ratio_is_warning(self):
        # 150 issues / 100 stars = 1.5 ratio > 0.1 threshold
        repo = _make_repo(
            pushed_at=datetime.now(timezone.utc) - timedelta(days=10),
            open_issues_count=150,
            license_name="MIT",
        )
        result = compute_health(repo)
        assert result["status"] == "warning"
        assert "High issue-to-star ratio" in result["issues"]

    def test_large_repo_many_issues_is_healthy(self):
        # 500 issues / 21000 stars = 0.024 ratio < 0.1 threshold
        repo = _make_repo(
            stars=21000,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=10),
            open_issues_count=500,
            license_name="MIT",
        )
        result = compute_health(repo)
        assert result["status"] == "healthy"
        assert result["issues"] == []

    def test_no_license_is_warning(self):
        repo = _make_repo(
            pushed_at=datetime.now(timezone.utc) - timedelta(days=10),
            license_name="",
        )
        result = compute_health(repo)
        assert result["status"] == "warning"
        assert "No license" in result["issues"]

    def test_multiple_warnings(self):
        repo = _make_repo(
            pushed_at=datetime.now(timezone.utc) - timedelta(days=400),
            open_issues_count=200,
            license_name="",
        )
        result = compute_health(repo)
        assert result["status"] == "warning"
        assert len(result["issues"]) == 3

    def test_no_pushed_at(self):
        repo = _make_repo(pushed_at=None, license_name="MIT")
        result = compute_health(repo)
        assert result["status"] == "healthy"
