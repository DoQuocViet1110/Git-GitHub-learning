"""In-memory adapters for the GitRepo and Builder seams.

These are the second adapter at each seam; the first are GitRepo and
Builder themselves. Tests drive the real Watcher and BuildPipeline through
the same interface the production wiring uses.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Dict, List, Optional

from build_watcher.models import BuildOutcome, Commit


class FakeRepo:
    """Scripted history: a list of commits plus the file content at each."""

    def __init__(self, head: str = "", branches=()) -> None:
        self.commits: List[Commit] = []
        self.files: Dict[str, str] = {}
        self.head = head
        self.branches = set(branches)
        self.fetches = 0
        self.worktrees_created: List[str] = []

    # -- test helpers ---------------------------------------------------

    def push_request(self, sha: str, text: str, email: str = "dev@example.com") -> Commit:
        commit = Commit(
            sha=sha,
            author_email=email,
            author_name="Dev",
            committed_at="2026-08-22T10:00:00+07:00",
            subject="build request",
        )
        self.commits.append(commit)
        self.files[sha] = text
        self.head = sha
        return commit

    # -- GitRepo interface ----------------------------------------------

    def fetch(self) -> None:
        self.fetches += 1

    def remote_head(self, branch: str) -> str:
        return self.head

    def ref_exists(self, branch: str) -> bool:
        return branch in self.branches

    def commits_touching(self, branch, path, since=None, limit=100):
        if since is None:
            return self.commits[:limit]
        known = [c.sha for c in self.commits]
        index = known.index(since) + 1 if since in known else 0
        return self.commits[index:][:limit]

    def file_at(self, sha: str, path: str) -> str:
        return self.files[sha]

    @contextlib.contextmanager
    def worktree(self, branch: str):
        self.worktrees_created.append(branch)
        yield Path("/fake/worktree/{0}".format(branch.replace("/", "-")))


class FakeBuilder:
    """Returns a canned outcome and records what it was asked to build."""

    def __init__(self, succeeded: bool = True, message: str = "build finished") -> None:
        self.succeeded = succeeded
        self.message = message
        self.calls: List[tuple] = []

    def run(self, worktree, preset: Optional[str], tag: str) -> BuildOutcome:
        self.calls.append((str(worktree), preset, tag))
        return BuildOutcome(
            succeeded=self.succeeded,
            exit_code=0 if self.succeeded else 1,
            message=self.message,
            log_path=None,
            duration_seconds=1.0,
        )


class FakePackager:
    def __init__(self, archive: Optional[Path] = Path("/fake/out.zip")) -> None:
        self.archive = archive
        self.calls: List[str] = []

    def package(self, worktree, tag: str) -> Optional[Path]:
        self.calls.append(tag)
        return self.archive
