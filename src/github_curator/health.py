"""Repository health assessment for github-curator."""

from __future__ import annotations

from datetime import datetime, timezone

from github_curator.models import RepoInfo


def compute_health(repo: RepoInfo) -> dict:
    """Compute health status for a repository.

    Returns:
        Dictionary with "status" ("healthy", "warning", "critical")
        and "issues" (list of problem descriptions).
    """
    issues: list[str] = []

    if repo.archived:
        issues.append("Archived")

    if repo.pushed_at is not None:
        now = datetime.now(timezone.utc)
        pushed_at = repo.pushed_at
        if pushed_at.tzinfo is None:
            pushed_at = pushed_at.replace(tzinfo=timezone.utc)
        age_days = (now - pushed_at).days
        if age_days > 365 * 2:
            issues.append("No updates for >2 years")
        elif age_days > 365:
            issues.append("No updates for >1 year")

    issue_star_ratio = repo.open_issues_count / max(repo.stars, 1)
    if issue_star_ratio > 0.1:
        issues.append("High issue-to-star ratio")

    if repo.license_name == "":
        issues.append("No license")

    # Determine status
    critical_messages = {"Archived", "No updates for >2 years"}
    has_critical = any(msg in critical_messages for msg in issues)

    if has_critical:
        status = "critical"
    elif issues:
        status = "warning"
    else:
        status = "healthy"

    return {"status": status, "issues": issues}
