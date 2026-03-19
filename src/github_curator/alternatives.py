"""Find alternative/replacement repositories for stale or archived repos."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from github_curator.models import RepoInfo


ConfidenceLevel = Literal["high", "medium", "low"]


# Common English stop words to filter out from keyword extraction
_STOP_WORDS = frozenset(
    "a an the and or but in on at to for of is it this that with from by as be "
    "are was were been has have had do does did will would shall should may might "
    "can could not no nor so if then than too very also just about above after "
    "before between each few more most other some such only own same through "
    "during out up down off over under again further once here there when where "
    "which while who whom what how all any both each every".split()
)


def extract_keywords(full_name: str, description: str) -> list[str]:
    """Extract search keywords from a repo name and description.

    Splits on non-alphanumeric characters, lowercases, removes stop words
    and very short tokens. Returns deduplicated keywords preserving order.
    """
    # Combine repo name (without owner) and description
    repo_name = full_name.split("/")[-1] if "/" in full_name else full_name
    raw = f"{repo_name} {description}"
    tokens = re.split(r"[^a-zA-Z0-9]+", raw.lower())
    seen: set[str] = set()
    keywords: list[str] = []
    for token in tokens:
        if len(token) < 2 or token in _STOP_WORDS or token in seen:
            continue
        seen.add(token)
        keywords.append(token)
    return keywords


def _compute_confidence(
    original: RepoInfo,
    replacement: RepoInfo,
    source: Literal["fork", "parent", "search"],
) -> ConfidenceLevel:
    """Compute a confidence level for a suggested alternative.

    - "high": direct fork/parent with more stars or more recent activity
    - "medium": fork with less stars but more recent activity
    - "low": similar repo found by keyword search
    """
    if source == "search":
        return "low"
    if source == "parent":
        return "high"
    # source == "fork"
    if replacement.stars >= original.stars:
        return "high"
    return "medium"


@dataclass
class Alternative:
    """A suggested replacement for a stale or archived repository."""

    original: RepoInfo
    replacement: RepoInfo
    reason: str  # e.g. "Active fork (1,200 stars, last push 2026-02)"
    confidence: ConfidenceLevel = "medium"


def find_alternatives(repo: RepoInfo, api) -> list[Alternative]:
    """Find replacement candidates for a stale/archived repo.

    Strategies:
      1. If the repo is an original, check its most-starred forks for activity.
      2. If the repo is a fork, check whether its parent is more active.
      3. Search GitHub for repos with similar topics/description.

    Args:
        repo: The repository to find alternatives for.
        api: A GitHubAPI instance.

    Returns:
        List of Alternative suggestions, sorted by replacement stars descending.
    """
    alternatives: list[Alternative] = []
    seen_full_names: set[str] = {repo.full_name}

    # Strategy 1: Find active forks (only if this repo is the original)
    if repo.is_fork is False:
        try:
            forks = api.get_top_forks(repo.full_name, limit=5)
            for fork in forks:
                if fork.stars > repo.stars * 0.1 and fork.pushed_at and repo.pushed_at:
                    if fork.pushed_at > repo.pushed_at:
                        confidence = _compute_confidence(repo, fork, "fork")
                        reason = (
                            f"Active fork ({fork.stars:,} stars, "
                            f"last push {fork.pushed_at.strftime('%Y-%m')})"
                        )
                        alternatives.append(
                            Alternative(
                                original=repo,
                                replacement=fork,
                                reason=reason,
                                confidence=confidence,
                            )
                        )
                        seen_full_names.add(fork.full_name)
        except Exception:
            pass

    # Strategy 2: If this repo is a fork, check if the parent is more active
    if repo.is_fork and repo.parent_full_name:
        try:
            parent = api.get_repo_info_by_fullname(repo.parent_full_name)
            if parent.pushed_at and repo.pushed_at and parent.pushed_at > repo.pushed_at:
                confidence = _compute_confidence(repo, parent, "parent")
                reason = f"Original repo is more active ({parent.stars:,} stars)"
                alternatives.append(
                    Alternative(
                        original=repo,
                        replacement=parent,
                        reason=reason,
                        confidence=confidence,
                    )
                )
                seen_full_names.add(parent.full_name)
        except Exception:
            pass

    # Strategy 3: Search for similar repos by topic keywords
    try:
        similar = api.search_similar_repos(repo, max_results=5)
        for sim in similar:
            if sim.full_name in seen_full_names:
                continue
            if sim.archived:
                continue
            # Must have more stars or more recent push than original
            more_stars = sim.stars > repo.stars
            more_recent = (
                sim.pushed_at is not None
                and repo.pushed_at is not None
                and sim.pushed_at > repo.pushed_at
            )
            if more_stars or more_recent:
                confidence = _compute_confidence(repo, sim, "search")
                lang_note = f", {sim.language}" if sim.language else ""
                reason = f"Similar repo ({sim.stars:,} stars{lang_note})"
                alternatives.append(
                    Alternative(
                        original=repo,
                        replacement=sim,
                        reason=reason,
                        confidence=confidence,
                    )
                )
                seen_full_names.add(sim.full_name)
    except Exception:
        pass

    # Sort by replacement stars descending
    alternatives.sort(key=lambda a: a.replacement.stars, reverse=True)
    return alternatives
