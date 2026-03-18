"""Wrapper around PyGithub / GitHub REST API."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Optional

from github import Auth, Github, GithubException, RateLimitExceededException

from github_curator.models import RepoInfo

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
                        _RATE_LIMIT_WAIT_SECONDS,
                    )
                    time.sleep(min(wait, _RATE_LIMIT_WAIT_SECONDS))
                else:
                    raise

    def get_repo_info(self, owner: str, repo: str) -> RepoInfo:
        """Fetch information about a single repository."""

        def _fetch():
            r = self._client.get_repo(f"{owner}/{repo}")
            return RepoInfo(
                owner=owner,
                name=repo,
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
            return False, f"HTTP {e.status}: {e.data.get('message', 'Unknown error')}"
        except Exception as e:
            return False, str(e)

    def search_repos_by_topic(self, topic: str, max_results: int = 50) -> list:
        """Search GitHub repos by topic and return as RepoRef list.

        Args:
            topic: GitHub topic to search for.
            max_results: Maximum number of results to return.

        Returns:
            List of RepoRef sorted by stars descending.
        """
        from github_curator.parser import RepoRef

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
