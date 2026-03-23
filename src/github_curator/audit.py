"""Complete repository audit: health + links + dedupe + trends in one pass."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from github_curator.alternatives import Alternative
from github_curator.dedupe import find_duplicates
from github_curator.health import compute_health
from github_curator.models import RepoInfo
from github_curator.parser import RepoRef
from github_curator.trend import RepoTrend, analyze_trend, build_comparative_summary


@dataclass
class AuditResult:
    """Complete audit result for a set of repositories."""

    total_repos: int = 0
    total_stars: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    healthy: list[tuple[RepoInfo, dict]] = field(default_factory=list)
    warnings: list[tuple[RepoInfo, dict]] = field(default_factory=list)
    critical: list[tuple[RepoInfo, dict]] = field(default_factory=list)
    broken_links: list[tuple[str, str]] = field(default_factory=list)
    alternatives: list[tuple[RepoInfo, dict, list[Alternative]]] = field(default_factory=list)
    duplicate_groups: list[list[RepoInfo]] = field(default_factory=list)
    trends: list[RepoTrend] = field(default_factory=list)


def run_audit(
    refs: list[RepoRef],
    api,
    check_alternatives: bool = True,
    check_trends: bool = True,
) -> AuditResult:
    """Run a complete audit: health + links + dedupe + trends.

    Args:
        refs: List of repository references to audit.
        api: A GitHubAPI instance.
        check_alternatives: Whether to search for alternatives for problem repos.
        check_trends: Whether to compute trend analysis.

    Returns:
        AuditResult with all analysis data.
    """
    from github_curator.alternatives import find_alternatives

    result = AuditResult()
    repos: list[RepoInfo] = []
    lang_counter: Counter[str] = Counter()

    # Phase 1: Fetch repo info and check links + health
    for ref in refs:
        try:
            exists, error = api.check_repo_exists(ref.owner, ref.name)
            if not exists:
                result.broken_links.append((f"{ref.owner}/{ref.name}", error or "Unknown"))
                continue

            info = api.get_repo_info(ref.owner, ref.name)
            repos.append(info)
            lang_counter[info.language or "Unknown"] += 1

            h = compute_health(info)
            if h["status"] == "critical":
                result.critical.append((info, h))
            elif h["status"] == "warning":
                result.warnings.append((info, h))
            else:
                result.healthy.append((info, h))
        except Exception as e:
            result.broken_links.append((f"{ref.owner}/{ref.name}", str(e)))

    result.total_repos = len(repos) + len(result.broken_links)
    result.total_stars = sum(r.stars for r in repos)
    result.languages = dict(lang_counter.most_common())

    # Phase 2: Find alternatives for problem repos
    if check_alternatives:
        problem_repos = result.critical + result.warnings
        for info, h in problem_repos:
            try:
                alts = find_alternatives(info, api)
                if alts:
                    result.alternatives.append((info, h, alts))
            except Exception:
                pass

    # Phase 3: Duplicate detection
    if repos:
        result.duplicate_groups = find_duplicates(repos)

    # Phase 4: Trend analysis
    if check_trends and repos:
        result.trends = sorted(
            [analyze_trend(r) for r in repos],
            key=lambda t: (t.activity_score, t.monthly_star_rate),
            reverse=True,
        )

    return result


def audit_to_markdown(result: AuditResult, topic: str | None = None) -> str:
    """Convert an AuditResult to a Markdown report.

    Args:
        result: The audit result to format.
        topic: Optional topic name for the report header.

    Returns:
        Markdown string.
    """
    lines: list[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Header
    topic_label = f" (topic: {topic})" if topic else ""
    lines.append(f"# Audit Report: {result.total_repos} repositories{topic_label}")
    lines.append(f"_Generated: {now}_\n")

    # Overview
    num_langs = len(result.languages)
    lines.append("## Overview")
    lines.append(f"- **{result.total_repos}** repos analyzed")
    lines.append(f"- **{result.total_stars:,}** total stars")
    lines.append(f"- **{num_langs}** languages")
    lines.append(
        f"- {len(result.healthy)} healthy / "
        f"{len(result.warnings)} warning / "
        f"{len(result.critical)} critical / "
        f"{len(result.broken_links)} broken"
    )
    lines.append("")

    # Action Required
    if result.critical or result.broken_links:
        lines.append("## Action Required")
        lines.append("")
        lines.append("### Critical")
        for info, h in result.critical:
            pushed_str = info.pushed_at.strftime("%Y-%m") if info.pushed_at else "N/A"
            issues_str = ", ".join(h["issues"])
            lines.append(f"- **{info.full_name}** ({info.stars:,} stars, last push {pushed_str}) -- {issues_str}")
            # Check for alternatives
            for alt_info, _, alts in result.alternatives:
                if alt_info.full_name == info.full_name:
                    for alt in alts[:2]:
                        alt_pushed = alt.replacement.pushed_at.strftime("%Y-%m") if alt.replacement.pushed_at else "N/A"
                        lines.append(
                            f"  - Alternative: [{alt.replacement.full_name}]({alt.replacement.url}) "
                            f"({alt.replacement.stars:,} stars, {alt.confidence} confidence)"
                        )
        if result.broken_links:
            lines.append("")
            lines.append("### Broken Links")
            for name, error in result.broken_links:
                lines.append(f"- **{name}** -- {error}")
        lines.append("")

    # Warnings
    if result.warnings:
        lines.append("## Warnings")
        for info, h in result.warnings:
            pushed_str = info.pushed_at.strftime("%Y-%m") if info.pushed_at else "N/A"
            issues_str = ", ".join(h["issues"])
            lines.append(f"- **{info.full_name}** ({info.stars:,} stars, last push {pushed_str}) -- {issues_str}")
        lines.append("")

    # Healthy (top 5 by stars)
    if result.healthy:
        lines.append("## Healthy Repositories")
        top_healthy = sorted(result.healthy, key=lambda x: -x[0].stars)[:5]
        for info, _ in top_healthy:
            lines.append(f"- [{info.full_name}]({info.url}) ({info.stars:,} stars)")
        remaining = len(result.healthy) - len(top_healthy)
        if remaining > 0:
            lines.append(f"- ...and {remaining} more")
        lines.append("")

    # Trends
    if result.trends:
        insights = build_comparative_summary(result.trends)
        if insights:
            lines.append("## Trends")
            for line in insights:
                lines.append(f"- {line}")
            lines.append("")

    # Duplicates
    if result.duplicate_groups:
        lines.append("## Duplicates Found")
        for i, group in enumerate(result.duplicate_groups, 1):
            best = max(group, key=lambda r: r.stars)
            names = [r.full_name for r in sorted(group, key=lambda r: -r.stars)]
            lines.append(f"- Group {i}: {' / '.join(names)} (recommended: {best.full_name})")
        lines.append("")

    return "\n".join(lines) + "\n"


def audit_to_json(result: AuditResult, topic: str | None = None) -> str:
    """Convert an AuditResult to a JSON string.

    Args:
        result: The audit result to format.
        topic: Optional topic name.

    Returns:
        JSON string.
    """
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
        "overview": {
            "total_repos": result.total_repos,
            "total_stars": result.total_stars,
            "languages": result.languages,
            "healthy": len(result.healthy),
            "warnings": len(result.warnings),
            "critical": len(result.critical),
            "broken_links": len(result.broken_links),
        },
        "critical": [
            {
                "full_name": info.full_name,
                "stars": info.stars,
                "issues": h["issues"],
                "last_push": info.pushed_at.isoformat() if info.pushed_at else None,
            }
            for info, h in result.critical
        ],
        "warnings": [
            {
                "full_name": info.full_name,
                "stars": info.stars,
                "issues": h["issues"],
                "last_push": info.pushed_at.isoformat() if info.pushed_at else None,
            }
            for info, h in result.warnings
        ],
        "broken_links": [
            {"name": name, "error": error}
            for name, error in result.broken_links
        ],
        "alternatives": [
            {
                "original": info.full_name,
                "suggestions": [
                    {
                        "full_name": alt.replacement.full_name,
                        "stars": alt.replacement.stars,
                        "reason": alt.reason,
                        "confidence": alt.confidence,
                        "url": alt.replacement.url,
                    }
                    for alt in alts
                ],
            }
            for info, _, alts in result.alternatives
        ],
        "duplicate_groups": [
            [r.full_name for r in group]
            for group in result.duplicate_groups
        ],
        "trends": [t.to_dict() for t in result.trends[:10]] if result.trends else [],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
