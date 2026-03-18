"""Tests for github_curator.updater."""

from unittest.mock import MagicMock, patch

from github_curator.models import RepoInfo
from github_curator.parser import RepoRef
from github_curator.updater import _update_line_stars, update_awesome_stars


def _make_ref(owner="alice", name="repo"):
    return RepoRef(owner=owner, name=name, url=f"https://github.com/{owner}/{name}")


def _make_info(owner="alice", name="repo", stars=200):
    return RepoInfo(owner=owner, name=name, stars=stars)


def test_update_line_stars_with_badge():
    line = "- [alice/repo](https://github.com/alice/repo) ![Stars](https://img.shields.io/github/stars/alice/repo)"
    ref = _make_ref()
    info = _make_info(stars=500)
    result = _update_line_stars(line, ref, info)
    assert "![Stars](https://img.shields.io/github/stars/alice/repo)" in result


def test_update_line_stars_no_badge():
    line = "- [alice/repo](https://github.com/alice/repo)"
    ref = _make_ref()
    info = _make_info(stars=123)
    result = _update_line_stars(line, ref, info)
    assert "![Stars](https://img.shields.io/github/stars/alice/repo)" in result
    # Badge should be appended after the link
    assert result.index("![Stars]") > result.index("alice/repo)")


def test_update_awesome_stars_dry_run(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text(
        "# Repos\n- [alice/repo](https://github.com/alice/repo)\n",
        encoding="utf-8",
    )

    mock_api = MagicMock()
    mock_api.get_repo_info.return_value = _make_info(stars=999)

    diffs = update_awesome_stars(md_file, api=mock_api, dry_run=True)

    # File should not be modified
    content = md_file.read_text(encoding="utf-8")
    assert "999" not in content

    # But diffs should be reported
    assert len(diffs) == 1
    assert diffs[0].new_stars == 999
