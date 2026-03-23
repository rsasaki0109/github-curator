"""Tests for audit module."""

from datetime import datetime, timedelta, timezone

from github_curator.audit import AuditResult, audit_to_json, audit_to_markdown, run_audit
from github_curator.models import RepoInfo
from github_curator.parser import RepoRef


def _make_repo(owner="test", name="repo", stars=100, **kwargs) -> RepoInfo:
    defaults = dict(
        owner=owner,
        name=name,
        stars=stars,
        pushed_at=datetime.now(timezone.utc) - timedelta(days=10),
        license_name="MIT",
        created_at=datetime.now(timezone.utc) - timedelta(days=365),
    )
    defaults.update(kwargs)
    return RepoInfo(**defaults)


class FakeAPI:
    """Fake GitHubAPI for testing."""

    def __init__(self, repos: dict[str, RepoInfo], broken: set[str] | None = None):
        self._repos = repos
        self._broken = broken or set()

    def check_repo_exists(self, owner: str, repo: str):
        key = f"{owner}/{repo}"
        if key in self._broken:
            return False, "404 Not Found"
        if key in self._repos:
            return True, None
        return False, "404 Not Found"

    def get_repo_info(self, owner: str, repo: str) -> RepoInfo:
        key = f"{owner}/{repo}"
        if key not in self._repos:
            raise Exception(f"Not found: {key}")
        return self._repos[key]

    def get_top_forks(self, full_name: str, limit: int = 5):
        return []

    def search_similar_repos(self, repo: RepoInfo, max_results: int = 5):
        return []


class TestRunAudit:
    def test_healthy_repos(self):
        repo_a = _make_repo(owner="org", name="healthy1", stars=5000, language="Python")
        repo_b = _make_repo(owner="org", name="healthy2", stars=3000, language="C++")
        repos = {"org/healthy1": repo_a, "org/healthy2": repo_b}
        refs = [
            RepoRef(owner="org", name="healthy1", url="https://github.com/org/healthy1"),
            RepoRef(owner="org", name="healthy2", url="https://github.com/org/healthy2"),
        ]
        api = FakeAPI(repos)
        result = run_audit(refs, api, check_alternatives=False, check_trends=False)

        assert result.total_repos == 2
        assert result.total_stars == 8000
        assert len(result.healthy) == 2
        assert len(result.critical) == 0
        assert len(result.warnings) == 0
        assert len(result.broken_links) == 0

    def test_critical_repo(self):
        repo = _make_repo(
            owner="org", name="stale",
            stars=1000,
            archived=True,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=900),
        )
        repos = {"org/stale": repo}
        refs = [RepoRef(owner="org", name="stale", url="https://github.com/org/stale")]
        api = FakeAPI(repos)
        result = run_audit(refs, api, check_alternatives=False, check_trends=False)

        assert len(result.critical) == 1
        assert len(result.healthy) == 0
        info, h = result.critical[0]
        assert info.full_name == "org/stale"
        assert "Archived" in h["issues"]

    def test_warning_repo(self):
        repo = _make_repo(
            owner="org", name="warn",
            stars=500,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=400),
        )
        repos = {"org/warn": repo}
        refs = [RepoRef(owner="org", name="warn", url="https://github.com/org/warn")]
        api = FakeAPI(repos)
        result = run_audit(refs, api, check_alternatives=False, check_trends=False)

        assert len(result.warnings) == 1
        assert len(result.critical) == 0

    def test_broken_links(self):
        refs = [
            RepoRef(owner="org", name="gone", url="https://github.com/org/gone"),
        ]
        api = FakeAPI({}, broken={"org/gone"})
        result = run_audit(refs, api, check_alternatives=False, check_trends=False)

        assert len(result.broken_links) == 1
        assert result.broken_links[0] == ("org/gone", "404 Not Found")
        assert result.total_repos == 1

    def test_mixed_results(self):
        healthy = _make_repo(owner="org", name="good", stars=2000, language="Python")
        critical = _make_repo(
            owner="org", name="bad", stars=500, archived=True,
            pushed_at=datetime.now(timezone.utc) - timedelta(days=900),
        )
        repos = {"org/good": healthy, "org/bad": critical}
        refs = [
            RepoRef(owner="org", name="good", url="https://github.com/org/good"),
            RepoRef(owner="org", name="bad", url="https://github.com/org/bad"),
            RepoRef(owner="org", name="gone", url="https://github.com/org/gone"),
        ]
        api = FakeAPI(repos, broken={"org/gone"})
        result = run_audit(refs, api, check_alternatives=False, check_trends=False)

        assert result.total_repos == 3
        assert len(result.healthy) == 1
        assert len(result.critical) == 1
        assert len(result.broken_links) == 1

    def test_languages_counted(self):
        repo_a = _make_repo(owner="a", name="r1", language="Python")
        repo_b = _make_repo(owner="a", name="r2", language="Python")
        repo_c = _make_repo(owner="a", name="r3", language="C++")
        repos = {"a/r1": repo_a, "a/r2": repo_b, "a/r3": repo_c}
        refs = [
            RepoRef(owner="a", name="r1", url="u"),
            RepoRef(owner="a", name="r2", url="u"),
            RepoRef(owner="a", name="r3", url="u"),
        ]
        api = FakeAPI(repos)
        result = run_audit(refs, api, check_alternatives=False, check_trends=False)

        assert result.languages["Python"] == 2
        assert result.languages["C++"] == 1

    def test_trends_computed(self):
        repo = _make_repo(owner="org", name="repo", stars=5000)
        repos = {"org/repo": repo}
        refs = [RepoRef(owner="org", name="repo", url="u")]
        api = FakeAPI(repos)
        result = run_audit(refs, api, check_alternatives=False, check_trends=True)

        assert len(result.trends) == 1
        assert result.trends[0].repo.full_name == "org/repo"


class TestAuditToMarkdown:
    def test_basic_report(self):
        result = AuditResult(
            total_repos=3,
            total_stars=8000,
            languages={"Python": 2, "C++": 1},
            healthy=[
                (_make_repo(owner="org", name="good", stars=5000), {"status": "healthy", "issues": []}),
            ],
            warnings=[],
            critical=[
                (
                    _make_repo(owner="org", name="bad", stars=500, archived=True),
                    {"status": "critical", "issues": ["Archived"]},
                ),
            ],
            broken_links=[("org/gone", "404 Not Found")],
        )
        md = audit_to_markdown(result, topic="slam")

        assert "Audit Report: 3 repositories (topic: slam)" in md
        assert "8,000" in md
        assert "org/bad" in md
        assert "Archived" in md
        assert "org/gone" in md
        assert "404 Not Found" in md

    def test_no_problems(self):
        result = AuditResult(
            total_repos=2,
            total_stars=10000,
            languages={"Python": 2},
            healthy=[
                (_make_repo(owner="a", name="r1", stars=5000), {"status": "healthy", "issues": []}),
                (_make_repo(owner="a", name="r2", stars=5000), {"status": "healthy", "issues": []}),
            ],
        )
        md = audit_to_markdown(result)

        assert "Action Required" not in md
        assert "Healthy Repositories" in md


class TestAuditToJson:
    def test_json_structure(self):
        result = AuditResult(
            total_repos=2,
            total_stars=5000,
            languages={"Python": 2},
            healthy=[
                (_make_repo(owner="a", name="r1", stars=3000), {"status": "healthy", "issues": []}),
            ],
            critical=[
                (
                    _make_repo(owner="b", name="r2", stars=2000, archived=True),
                    {"status": "critical", "issues": ["Archived"]},
                ),
            ],
            broken_links=[("c/r3", "404")],
        )
        import json
        data = json.loads(audit_to_json(result, topic="test"))

        assert data["topic"] == "test"
        assert data["overview"]["total_repos"] == 2
        assert data["overview"]["total_stars"] == 5000
        assert data["overview"]["healthy"] == 1
        assert data["overview"]["critical"] == 1
        assert len(data["critical"]) == 1
        assert data["critical"][0]["full_name"] == "b/r2"
        assert len(data["broken_links"]) == 1
