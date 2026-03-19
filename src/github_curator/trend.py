"""Trend analysis for GitHub repositories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from github_curator.models import RepoInfo


@dataclass
class RepoTrend:
    """Trend analysis result for a repository."""

    repo: RepoInfo
    status: str  # "growing", "stable", "declining", "inactive"
    monthly_star_rate: float  # estimated stars per month
    activity_score: float  # 0-100 based on push recency + issues
    summary: str  # human-readable summary


def analyze_trend(repo: RepoInfo) -> RepoTrend:
    """Analyze growth and activity trend for a repo."""
    now = datetime.now(timezone.utc)

    # Estimate monthly star rate (rough: total stars / age in months)
    # We don't have historical data, so this is stars/month since creation.
    # A more accurate version would use the GitHub star history API.
    created_days = 365 * 3  # assume 3 years if unknown (conservative)
    monthly_star_rate = repo.stars / max(created_days / 30, 1)

    # Activity score based on push recency
    activity_score = 0.0
    days_since_push = None
    if repo.pushed_at:
        pushed_at = repo.pushed_at
        if pushed_at.tzinfo is None:
            pushed_at = pushed_at.replace(tzinfo=timezone.utc)
        days_since_push = (now - pushed_at).days
        if days_since_push <= 7:
            activity_score = 100
        elif days_since_push <= 30:
            activity_score = 80
        elif days_since_push <= 90:
            activity_score = 60
        elif days_since_push <= 365:
            activity_score = 30
        elif days_since_push <= 730:
            activity_score = 20
        else:
            activity_score = 10

    # Adjust for archived
    if repo.archived:
        activity_score = 0

    # Determine status
    if repo.archived or activity_score <= 10:
        status = "inactive"
    elif activity_score >= 60 and monthly_star_rate >= 50:
        status = "growing"
    elif activity_score >= 30:
        status = "stable"
    else:
        status = "declining"

    # Build summary
    parts = []
    parts.append(f"{repo.stars:,} stars")
    if monthly_star_rate >= 100:
        parts.append(f"~{monthly_star_rate:.0f} stars/month")
    if days_since_push is not None:
        if days_since_push <= 7:
            parts.append("updated this week")
        elif days_since_push <= 30:
            parts.append("updated this month")
        elif days_since_push <= 365:
            parts.append(f"last push {days_since_push} days ago")
        else:
            parts.append(f"inactive for {days_since_push // 365}+ years")
    if repo.archived:
        parts.append("ARCHIVED")

    summary = ", ".join(parts)

    return RepoTrend(
        repo=repo,
        status=status,
        monthly_star_rate=monthly_star_rate,
        activity_score=activity_score,
        summary=summary,
    )


def analyze_trends(repos: list[RepoInfo]) -> list[RepoTrend]:
    """Analyze trends for multiple repos, sorted by activity score."""
    trends = [analyze_trend(r) for r in repos]
    trends.sort(key=lambda t: (t.activity_score, t.monthly_star_rate), reverse=True)
    return trends
