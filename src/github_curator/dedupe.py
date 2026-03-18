"""Detect duplicate and related repositories in an awesome list."""

from __future__ import annotations

from github_curator.models import RepoInfo


def find_duplicates(repos: list[RepoInfo]) -> list[list[RepoInfo]]:
    """Find groups of related/duplicate repositories.

    Groups are formed by:
    - Repos that share the same parent_full_name (forks of the same upstream).
    - Repos where is_fork=True and their parent is also in the list.

    Args:
        repos: List of RepoInfo with fork metadata populated.

    Returns:
        List of groups, where each group is a list of related RepoInfo.
    """
    # Build a set of all repo full names for quick lookup
    repo_names = {r.full_name.lower() for r in repos}

    # Group by parent_full_name
    parent_groups: dict[str, list[RepoInfo]] = {}
    for repo in repos:
        if repo.parent_full_name:
            key = repo.parent_full_name.lower()
            parent_groups.setdefault(key, []).append(repo)

    # Build final groups
    groups: list[list[RepoInfo]] = []
    seen: set[str] = set()

    for parent_name, forks in parent_groups.items():
        if len(forks) < 2 and parent_name not in repo_names:
            # Single fork whose parent is not in the list -- skip
            continue

        group: list[RepoInfo] = []
        # Add the parent if it's in our list
        for repo in repos:
            if repo.full_name.lower() == parent_name and repo.full_name.lower() not in seen:
                group.append(repo)
                seen.add(repo.full_name.lower())

        # Add all forks
        for fork in forks:
            if fork.full_name.lower() not in seen:
                group.append(fork)
                seen.add(fork.full_name.lower())

        if len(group) >= 2:
            groups.append(group)

    return groups
