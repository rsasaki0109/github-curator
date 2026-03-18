"""Tests for diff functionality."""

from github_curator.differ import diff_lists


OLD_MARKDOWN = """\
# Awesome List

- [repo-a](https://github.com/owner/repo-a) - Description A
- [repo-b](https://github.com/owner/repo-b) - Description B
- [repo-c](https://github.com/owner/repo-c) - Description C
"""

NEW_MARKDOWN = """\
# Awesome List

- [repo-b](https://github.com/owner/repo-b) - Description B
- [repo-c](https://github.com/owner/repo-c) - Description C
- [repo-d](https://github.com/owner/repo-d) - Description D
"""


class TestDiffLists:
    def test_added_repos(self):
        result = diff_lists(OLD_MARKDOWN, NEW_MARKDOWN)
        added_names = [r.name for r in result.added]
        assert "repo-d" in added_names

    def test_removed_repos(self):
        result = diff_lists(OLD_MARKDOWN, NEW_MARKDOWN)
        removed_names = [r.name for r in result.removed]
        assert "repo-a" in removed_names

    def test_common_repos(self):
        result = diff_lists(OLD_MARKDOWN, NEW_MARKDOWN)
        common_names = [r.name for r in result.common]
        assert "repo-b" in common_names
        assert "repo-c" in common_names

    def test_no_changes(self):
        result = diff_lists(OLD_MARKDOWN, OLD_MARKDOWN)
        assert result.added == []
        assert result.removed == []
        assert len(result.common) == 3

    def test_empty_old(self):
        result = diff_lists("", NEW_MARKDOWN)
        assert len(result.added) == 3
        assert result.removed == []

    def test_empty_both(self):
        result = diff_lists("", "")
        assert result.added == []
        assert result.removed == []
        assert result.common == []
