"""Value types passed between modules.

All frozen: nothing downstream mutates what it was handed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Commit:
    """One commit on the trigger branch."""

    sha: str
    author_email: str
    author_name: str
    committed_at: str
    subject: str

    @property
    def short_sha(self) -> str:
        return self.sha[:12]


@dataclass(frozen=True)
class ParsedRequest:
    """What a request file asked for, after format validation."""

    branch: str
    preset: Optional[str]


@dataclass(frozen=True)
class BuildRequest:
    """A parsed request tied back to the commit that carried it."""

    commit: Commit
    branch: str
    preset: Optional[str]

    @property
    def tag(self) -> str:
        """Filesystem/tag-safe identifier for this request's outputs."""
        safe_branch = self.branch.replace("/", "-")
        parts = [safe_branch, self.commit.short_sha]
        if self.preset:
            parts.insert(1, self.preset)
        return "-".join(parts)


@dataclass(frozen=True)
class BuildOutcome:
    """Result of running the build script once."""

    succeeded: bool
    exit_code: int
    message: str
    log_path: Optional[Path]
    duration_seconds: float
