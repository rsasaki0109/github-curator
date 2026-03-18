"""Tests for github_curator.input module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from github_curator.input import resolve_repos
from github_curator.parser import RepoRef


class TestResolveReposFromURLs:
    def test_single_url(self):
        refs = resolve_repos(urls=["https://github.com/owner/repo"])
        assert len(refs) == 1
        assert refs[0].owner == "owner"
        assert refs[0].name == "repo"

    def test_multiple_urls(self):
        refs = resolve_repos(urls=[
            "https://github.com/org/repo1",
            "https://github.com/org/repo2",
        ])
        assert len(refs) == 2
        assert refs[0].name == "repo1"
        assert refs[1].name == "repo2"

    def test_url_with_git_suffix(self):
        refs = resolve_repos(urls=["https://github.com/owner/repo.git"])
        assert len(refs) == 1
        assert refs[0].name == "repo"

    def test_invalid_url_skipped(self):
        refs = resolve_repos(urls=["https://example.com/not-github"])
        assert len(refs) == 0

    def test_empty_urls_list(self):
        refs = resolve_repos(urls=[])
        assert len(refs) == 0


class TestResolveReposFromFile:
    def test_markdown_file(self, tmp_path):
        md = tmp_path / "repos.md"
        md.write_text(
            "# Repos\n"
            "- [repo1](https://github.com/org/repo1) - desc\n"
            "- [repo2](https://github.com/org/repo2) - desc\n",
            encoding="utf-8",
        )
        refs = resolve_repos(file=md)
        assert len(refs) == 2
        assert refs[0].owner == "org"
        assert refs[0].name == "repo1"

    def test_plain_text_with_urls(self, tmp_path):
        txt = tmp_path / "repos.txt"
        txt.write_text(
            "https://github.com/owner/alpha\n"
            "https://github.com/owner/beta\n",
            encoding="utf-8",
        )
        refs = resolve_repos(file=txt)
        assert len(refs) == 2

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="File not found"):
            resolve_repos(file=tmp_path / "nonexistent.md")

    def test_empty_file(self, tmp_path):
        md = tmp_path / "empty.md"
        md.write_text("# No repos here\n", encoding="utf-8")
        refs = resolve_repos(file=md)
        assert len(refs) == 0


class TestDeduplication:
    def test_duplicate_urls_deduplicated(self):
        refs = resolve_repos(urls=[
            "https://github.com/Org/Repo",
            "https://github.com/org/repo",
        ])
        assert len(refs) == 1

    def test_duplicate_across_url_and_file(self, tmp_path):
        md = tmp_path / "repos.md"
        md.write_text(
            "- [repo](https://github.com/org/repo) - desc\n",
            encoding="utf-8",
        )
        refs = resolve_repos(
            urls=["https://github.com/org/repo"],
            file=md,
        )
        assert len(refs) == 1


class TestResolveReposFromTopic:
    def test_topic_search(self):
        mock_api = MagicMock()
        mock_api.search_repos_by_topic.return_value = [
            RepoRef(owner="org", name="slam-lib", url="https://github.com/org/slam-lib"),
        ]

        with patch("github_curator.github_api.GitHubAPI") as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_api)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            refs = resolve_repos(topic="slam", max_results=10)

        assert len(refs) == 1
        assert refs[0].name == "slam-lib"
        mock_api.search_repos_by_topic.assert_called_once_with("slam", max_results=10)


class TestNoInput:
    def test_no_input_returns_empty(self):
        refs = resolve_repos()
        assert len(refs) == 0
