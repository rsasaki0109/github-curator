"""Wrapper around PyGithub / GitHub REST API."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Optional

from github import Auth, Github, GithubException, RateLimitExceededException

from github_curator.models import RepoInfo
from github_curator.parser import RepoRef

_DEFAULT_MAX_RETRIES = 3
_RATE_LIMIT_WAIT_SECONDS = 60


class GitHubAPI:
    """GitHub API client with rate-limit handling."""

    def __init__(self, token: Optional[str] = None) -> None:
        self._token = token or os.environ.get("GITHUB_TOKEN", "")
        if self._token:
            auth = Auth.Token(self._token)
            self._client = Github(auth=auth)
        else:
            self._client = Github()

    @property
    def authenticated(self) -> bool:
        return bool(self._token)

    def _retry_on_rate_limit(self, func, *args, max_retries: int = _DEFAULT_MAX_RETRIES, **kwargs):
        """Execute a function with retry logic for rate limiting."""
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except RateLimitExceededException:
                if attempt < max_retries - 1:
                    reset_time = self._client.get_rate_limit().core.reset
                    wait = max(
                        (reset_time - datetime.now(timezone.utc)).total_seconds() + 1,
                        1,
                    )
                    time.sleep(min(wait, 120))
                else:
                    raise

    @staticmethod
    def _to_repo_info(r) -> RepoInfo:
        """Convert a PyGithub Repository object to RepoInfo."""
        return RepoInfo(
            owner=r.owner.login,
            name=r.name,
            stars=r.stargazers_count,
            forks=r.forks_count,
            description=r.description or "",
            language=r.language or "",
            last_updated=r.updated_at.isoformat() if r.updated_at else "",
            archived=r.archived,
            url=r.html_url,
            topics=r.get_topics(),
            pushed_at=r.pushed_at,
            open_issues_count=r.open_issues_count,
            license_name=r.license.name if r.license else "",
            is_fork=r.fork,
            parent_full_name=r.parent.full_name if r.parent else "",
        )

    def get_repo_info(self, owner: str, repo: str) -> RepoInfo:
        """Fetch information about a single repository."""

        def _fetch():
            r = self._client.get_repo(f"{owner}/{repo}")
            return self._to_repo_info(r)

        return self._retry_on_rate_limit(_fetch)

    def get_repo_info_by_fullname(self, full_name: str) -> RepoInfo:
        """Get repo info by full name (owner/repo)."""

        def _fetch():
            r = self._client.get_repo(full_name)
            return self._to_repo_info(r)

        return self._retry_on_rate_limit(_fetch)

    def get_top_forks(self, full_name: str, limit: int = 5) -> list[RepoInfo]:
        """Get the most-starred forks of a repo.

        Args:
            full_name: Repository full name (owner/repo).
            limit: Maximum number of forks to return.

        Returns:
            List of RepoInfo for the top forks, sorted by stars descending.
        """

        def _fetch():
            repo = self._client.get_repo(full_name)
            forks = sorted(
                repo.get_forks(),
                key=lambda f: f.stargazers_count,
                reverse=True,
            )
            return [self._to_repo_info(f) for f in forks[:limit]]

        return self._retry_on_rate_limit(_fetch)

    def check_repo_exists(self, owner: str, repo: str) -> tuple[bool, Optional[str]]:
        """Check if a repository exists and is accessible.

        Returns:
            Tuple of (exists, error_message).
        """
        try:

            def _check():
                r = self._client.get_repo(f"{owner}/{repo}")
                return True, None

            return self._retry_on_rate_limit(_check)
        except GithubException as e:
            if isinstance(e.data, dict):
                msg = e.data.get("message", str(e))
            else:
                msg = str(e)
            return False, f"HTTP {e.status}: {msg}"
        except Exception as e:
            return False, str(e)

    def search_repos_by_topic(self, topic: str, max_results: int = 50) -> list[RepoRef]:
        """Search GitHub repos by topic and return as RepoRef list.

        Args:
            topic: GitHub topic to search for.
            max_results: Maximum number of results to return.

        Returns:
            List of RepoRef sorted by stars descending.
        """
        repos = self._client.search_repositories(
            query=f"topic:{topic}",
            sort="stars",
            order="desc",
        )
        refs = []
        for repo in repos[:max_results]:
            refs.append(
                RepoRef(
                    owner=repo.owner.login,
                    name=repo.name,
                    url=repo.html_url,
                )
            )
        return refs

    def get_rate_limit_info(self) -> dict:
        """Return current rate limit status."""
        rl = self._client.get_rate_limit()
        return {
            "limit": rl.core.limit,
            "remaining": rl.core.remaining,
            "reset": rl.core.reset.isoformat(),
        }

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
