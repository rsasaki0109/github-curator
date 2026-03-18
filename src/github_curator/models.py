"""Data models for github-curator."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class RepoInfo:
    """Information about a GitHub repository.

    Designed to be compatible with arxiv-curator's Paper model
    for shared JSON export interoperability.
    """

    owner: str
    name: str
    stars: int = 0
    forks: int = 0
    description: str = ""
    language: str = ""
    last_updated: str = ""
    archived: bool = False
    url: str = ""
    topics: list[str] = field(default_factory=list)
    pushed_at: datetime | None = None
    open_issues_count: int = 0
    license_name: str = ""
    is_fork: bool = False
    parent_full_name: str = ""

    def __post_init__(self) -> None:
        if not self.url:
            self.url = f"https://github.com/{self.owner}/{self.name}"

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Uses a format compatible with arxiv-curator's Paper.to_dict().
        """
        data = asdict(self)
        data["type"] = "github_repo"
        data["full_name"] = self.full_name
        return data

    def to_markdown(self) -> str:
        """Format as a markdown list entry with star badge."""
        badge = f"![Stars](https://img.shields.io/github/stars/{self.full_name})"
        lang = f" `{self.language}`" if self.language else ""
        desc = f" - {self.description}" if self.description else ""
        archived_tag = " **[ARCHIVED]**" if self.archived else ""
        return f"- [{self.full_name}]({self.url}) {badge}{lang}{archived_tag}{desc}"

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> RepoInfo:
        """Create RepoInfo from a dictionary."""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


@dataclass
class StarDiff:
    """Represents a change in star count for a repository."""

    repo: RepoInfo
    old_stars: int
    new_stars: int

    @property
    def diff(self) -> int:
        return self.new_stars - self.old_stars

    @property
    def changed(self) -> bool:
        return self.old_stars != self.new_stars

    def __str__(self) -> str:
        sign = "+" if self.diff > 0 else ""
        return f"{self.repo.full_name}: {self.old_stars} -> {self.new_stars} ({sign}{self.diff})"
