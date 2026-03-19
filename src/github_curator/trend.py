"""Trend analysis for GitHub repositories."""

from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from github_curator.models import RepoInfo


@dataclass
class RepoTrend:
    """Trend analysis result for a repository."""

    repo: RepoInfo
    status: str  # "growing", "stable", "declining", "inactive"
    monthly_star_rate: float  # estimated stars per month
    activity_score: float  # 0-100 based on push recency + issues
    summary: str  # human-readable summary
    age_months: float  # actual age in months from created_at
    days_since_push: int | None  # days since last push
    open_issues_ratio: float  # open_issues / stars (health indicator)
    fork_ratio: float  # forks / stars (community indicator)

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dictionary."""
        return {
            "repo": self.repo.full_name,
            "stars": self.repo.stars,
            "forks": self.repo.forks,
            "status": self.status,
            "monthly_star_rate": round(self.monthly_star_rate, 1),
            "activity_score": round(self.activity_score, 1),
            "age_months": round(self.age_months, 1),
            "days_since_push": self.days_since_push,
            "open_issues_ratio": round(self.open_issues_ratio, 4),
            "fork_ratio": round(self.fork_ratio, 4),
            "summary": self.summary,
        }


def _activity_bar(score: float, width: int = 10) -> str:
    """Create a visual activity bar using Unicode blocks.

    Args:
        score: Activity score 0-100.
        width: Total bar width in characters.

    Returns:
        String like "████████░░" for score=80, width=10.
    """
    filled = round(score / 100 * width)
    filled = max(0, min(width, filled))
    return "\u2588" * filled + "\u2591" * (width - filled)


def analyze_trend(repo: RepoInfo) -> RepoTrend:
    """Analyze growth and activity trend for a repo."""
    now = datetime.now(timezone.utc)

    # Calculate actual age from created_at
    if repo.created_at:
        created_at = repo.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_months = max((now - created_at).days / 30, 1)
    else:
        # Fallback: assume 3 years if unknown
        age_months = 36.0

    monthly_star_rate = repo.stars / age_months

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

    # Activity breakdown ratios
    open_issues_ratio = repo.open_issues_count / max(repo.stars, 1)
    fork_ratio = repo.forks / max(repo.stars, 1)

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
        age_months=age_months,
        days_since_push=days_since_push,
        open_issues_ratio=open_issues_ratio,
        fork_ratio=fork_ratio,
    )


def analyze_trends(repos: list[RepoInfo]) -> list[RepoTrend]:
    """Analyze trends for multiple repos, sorted by activity score."""
    trends = [analyze_trend(r) for r in repos]
    trends.sort(key=lambda t: (t.activity_score, t.monthly_star_rate), reverse=True)
    return trends


def build_comparative_summary(trends: list[RepoTrend]) -> list[str]:
    """Build comparative insight lines for a set of trends.

    Returns a list of human-readable insight strings.
    """
    if not trends:
        return []

    insights: list[str] = []

    # Fastest growing
    fastest = max(trends, key=lambda t: t.monthly_star_rate)
    insights.append(
        f"Fastest growing: {fastest.repo.full_name} "
        f"({fastest.monthly_star_rate:.0f} stars/month)"
    )

    # Most active (most recently pushed)
    with_push = [t for t in trends if t.days_since_push is not None]
    if with_push:
        most_active = min(with_push, key=lambda t: t.days_since_push)
        insights.append(
            f"Most active: {most_active.repo.full_name} "
            f"(pushed {most_active.days_since_push} days ago)"
        )

    # Largest
    largest = max(trends, key=lambda t: t.repo.stars)
    insights.append(
        f"Largest: {largest.repo.full_name} ({largest.repo.stars:,} stars)"
    )

    # Rising star: young (<12 months) but already notable stars
    rising = [t for t in trends if t.age_months < 12 and t.repo.stars >= 100]
    if rising:
        best_rising = max(rising, key=lambda t: t.repo.stars)
        insights.append(
            f"Rising star: {best_rising.repo.full_name} "
            f"(only {best_rising.age_months:.0f} months old but already "
            f"{best_rising.repo.stars:,} stars)"
        )

    return insights


def build_sector_summary(trends: list[RepoTrend], topic: str) -> list[str]:
    """Build sector comparison lines when using --topic.

    Args:
        trends: List of analyzed trends.
        topic: The topic being analyzed.

    Returns:
        List of human-readable sector summary strings.
    """
    if not trends:
        return []

    lines: list[str] = []
    stars_list = [t.repo.stars for t in trends]
    avg_stars = statistics.mean(stars_list)
    lines.append(f"Topic '{topic}' average stars: {avg_stars:,.0f}")

    scores = [t.activity_score for t in trends]
    median_activity = statistics.median(scores)
    lines.append(f"Median activity score: {median_activity:.0f}")

    growing = sum(1 for t in trends if t.status == "growing")
    declining = sum(1 for t in trends if t.status in ("declining", "inactive"))
    lines.append(f"Growing: {growing}, Declining/Inactive: {declining}")

    return lines


def trends_to_json(
    trends: list[RepoTrend],
    topic: str | None = None,
) -> str:
    """Serialize trend analysis to JSON.

    Args:
        trends: List of analyzed trends.
        topic: Optional topic name for sector summary.

    Returns:
        JSON string.
    """
    data: dict = {
        "repos": [t.to_dict() for t in trends],
        "comparative": build_comparative_summary(trends),
    }
    if topic:
        data["sector"] = build_sector_summary(trends, topic)
    return json.dumps(data, ensure_ascii=False, indent=2)


def save_trends_json(
    trends: list[RepoTrend],
    output: Path,
    topic: str | None = None,
) -> None:
    """Save trend analysis to a JSON file."""
    output.write_text(trends_to_json(trends, topic=topic), encoding="utf-8")
