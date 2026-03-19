"""Find alternative/replacement repositories for stale or archived repos."""

from __future__ import annotations

from dataclasses import dataclass

from github_curator.models import RepoInfo


@dataclass
class Alternative:
    """A suggested replacement for a stale or archived repository."""

    original: RepoInfo
    replacement: RepoInfo
    reason: str  # e.g. "Active fork (1,200 stars, last push 2026-02)"


def find_alternatives(repo: RepoInfo, api) -> list[Alternative]:
    """Find replacement candidates for a stale/archived repo.

    Strategies:
      1. If the repo is an original, check its most-starred forks for activity.
      2. If the repo is a fork, check whether its parent is more active.

    Args:
        repo: The repository to find alternatives for.
        api: A GitHubAPI instance.

    Returns:
        List of Alternative suggestions, sorted by replacement stars descending.
    """
    alternatives: list[Alternative] = []

    # Strategy 1: Find active forks (only if this repo is the original)
    if repo.is_fork is False:
        try:
            forks = api.get_top_forks(repo.full_name, limit=5)
            for fork in forks:
                if fork.stars > repo.stars * 0.1 and fork.pushed_at and repo.pushed_at:
                    if fork.pushed_at > repo.pushed_at:
                        reason = (
                            f"Active fork ({fork.stars:,} stars, "
                            f"last push {fork.pushed_at.strftime('%Y-%m')})"
                        )
                        alternatives.append(
                            Alternative(original=repo, replacement=fork, reason=reason)
                        )
        except Exception:
            pass

    # Strategy 2: If this repo is a fork, check if the parent is more active
    if repo.is_fork and repo.parent_full_name:
        try:
            parent = api.get_repo_info_by_fullname(repo.parent_full_name)
            if parent.pushed_at and repo.pushed_at and parent.pushed_at > repo.pushed_at:
                reason = f"Original repo is more active ({parent.stars:,} stars)"
                alternatives.append(
                    Alternative(original=repo, replacement=parent, reason=reason)
                )
        except Exception:
            pass

    # Sort by replacement stars descending
    alternatives.sort(key=lambda a: a.replacement.stars, reverse=True)
    return alternatives
