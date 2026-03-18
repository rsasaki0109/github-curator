"""Tests for the GitHub API wrapper (using mocks)."""

from unittest.mock import MagicMock, patch

import pytest

from github_curator.github_api import GitHubAPI
from github_curator.models import RepoInfo


def _make_mock_repo(
    owner="testowner",
    name="testrepo",
    stars=100,
    forks=20,
    description="A test repo",
    language="Python",
    archived=False,
):
    """Create a mock GitHub repo object."""
    repo = MagicMock()
    repo.owner.login = owner
    repo.name = name
    repo.stargazers_count = stars
    repo.forks_count = forks
    repo.description = description
    repo.language = language
    repo.archived = archived
    repo.html_url = f"https://github.com/{owner}/{name}"
    repo.updated_at = MagicMock()
    repo.updated_at.isoformat.return_value = "2025-01-15T10:00:00"
    repo.get_topics.return_value = ["python", "testing"]
    return repo


class TestGetRepoInfo:
    @patch("github_curator.github_api.Github")
    def test_returns_repo_info(self, mock_github_cls):
        mock_client = MagicMock()
        mock_github_cls.return_value = mock_client
        mock_client.get_repo.return_value = _make_mock_repo()

        api = GitHubAPI()
        api._client = mock_client
        info = api.get_repo_info("testowner", "testrepo")

        assert isinstance(info, RepoInfo)
        assert info.owner == "testowner"
        assert info.name == "testrepo"
        assert info.stars == 100
        assert info.forks == 20
        assert info.language == "Python"
        assert info.description == "A test repo"
        assert info.archived is False

    @patch("github_curator.github_api.Github")
    def test_search_repos(self, mock_github_cls):
        mock_client = MagicMock()
        mock_github_cls.return_value = mock_client

        mock_results = MagicMock()
        mock_results.__getitem__ = MagicMock(
            side_effect=lambda s: [_make_mock_repo(), _make_mock_repo(name="repo2", stars=50)]
        )
        mock_client.search_repositories.return_value = mock_results

        api = GitHubAPI()
        api._client = mock_client
        repos = api.search_repos("language:python", max_results=2)

        assert len(repos) == 2
        assert repos[0].stars == 100
        assert repos[1].name == "repo2"


class TestCheckRepoExists:
    @patch("github_curator.github_api.Github")
    def test_existing_repo(self, mock_github_cls):
        mock_client = MagicMock()
        mock_github_cls.return_value = mock_client
        mock_client.get_repo.return_value = _make_mock_repo()

        api = GitHubAPI()
        api._client = mock_client
        exists, error = api.check_repo_exists("testowner", "testrepo")

        assert exists is True
        assert error is None
