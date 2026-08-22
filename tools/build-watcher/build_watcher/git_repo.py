"""Everything this tool needs from git, behind one interface.

Callers never build a git command line, never parse git output, and never
manage a worktree's lifetime. That plumbing lives here so the pipeline and
watcher can be tested against a fake that implements the same six methods.
"""

from __future__ import annotations

import contextlib
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple

from .models import Commit

# Unit/record separators: safe inside commit subjects, unlike newlines.
_FIELD = "\x1f"
_RECORD = "\x1e"
_FORMAT = _FIELD.join(["%H", "%ae", "%an", "%cI", "%s"]) + _RECORD

log = logging.getLogger(__name__)


class GitError(RuntimeError):
    """A git command failed."""


class GitRepo:
    """A local clone used only for watching and for spawning worktrees.

    The clone itself is never checked out to a build branch; builds happen
    in throwaway worktrees, so a build can never disturb the watch loop.
    """

    def __init__(
        self,
        path: Path,
        workspace: Path,
        remote: str = "origin",
        git_executable: str = "git",
        timeout: int = 600,
    ) -> None:
        self.path = Path(path)
        self.workspace = Path(workspace)
        self.remote = remote
        self.git = git_executable
        self.timeout = timeout

    # -- construction ---------------------------------------------------

    @classmethod
    def ensure_clone(
        cls,
        url: str,
        path: Path,
        workspace: Path,
        remote: str = "origin",
        git_executable: str = "git",
        timeout: int = 600,
    ) -> "GitRepo":
        """Return a repo at ``path``, cloning ``url`` there if needed."""
        path = Path(path)
        repo = cls(path, workspace, remote, git_executable, timeout)
        if (path / ".git").exists():
            return repo
        path.parent.mkdir(parents=True, exist_ok=True)
        log.info("cloning %s into %s", url, path)
        subprocess.run(
            [git_executable, "clone", "--origin", remote, url, str(path)],
            check=True,
            timeout=timeout,
        )
        return repo

    # -- reading --------------------------------------------------------

    def fetch(self) -> None:
        self._run(["fetch", "--prune", "--quiet", self.remote])

    def remote_head(self, branch: str) -> str:
        """SHA that ``branch`` points at on the remote, as of the last fetch."""
        return self._run(["rev-parse", self._remote_ref(branch)]).strip()

    def ref_exists(self, branch: str) -> bool:
        try:
            self._run(["rev-parse", "--verify", "--quiet", self._remote_ref(branch)])
            return True
        except GitError:
            return False

    def commits_touching(
        self,
        branch: str,
        path: str,
        since: Optional[str] = None,
        limit: int = 100,
    ) -> List[Commit]:
        """Commits on ``branch`` after ``since`` that changed ``path``.

        Oldest first, so requests are processed in the order they were
        pushed. Filtering by path here -- rather than in the caller -- is
        what keeps unrelated commits on the trigger branch from being
        mistaken for build requests.
        """
        rev = self._remote_ref(branch)
        if since:
            rev = "{0}..{1}".format(since, rev)
        out = self._run(
            [
                "log",
                "--reverse",
                "--no-merges",
                "--max-count={0}".format(limit),
                "--format={0}".format(_FORMAT),
                rev,
                "--",
                path,
            ]
        )
        return _parse_commits(out)

    def file_at(self, sha: str, path: str) -> str:
        """Contents of ``path`` as of ``sha``."""
        return self._run(["show", "{0}:{1}".format(sha, path)])

    # -- worktrees ------------------------------------------------------

    @contextlib.contextmanager
    def worktree(self, branch: str) -> Iterator[Tuple[Path, str]]:
        """Check ``branch`` out into a throwaway worktree for the block.

        Yields (path, sha) -- the exact commit checked out, resolved once
        up front and pinned by sha rather than by branch name. Without
        this, a caller has no honest way to say which commit a build
        artifact actually came from; publish_artifact uses it as the
        release's target_commitish instead of defaulting to whatever the
        repo's default branch happens to be (a real bug this replaced --
        see the commit message).

        Detached so nothing here can move a branch pointer, and removed on
        the way out even when the build raises.
        """
        self.workspace.mkdir(parents=True, exist_ok=True)
        sha = self.remote_head(branch)
        target = self.workspace / "wt-{0}".format(uuid.uuid4().hex[:12])
        self._run(["worktree", "add", "--detach", str(target), sha])
        try:
            yield target, sha
        finally:
            try:
                self._run(["worktree", "remove", "--force", str(target)])
            except GitError:
                log.warning("could not remove worktree %s; pruning", target)
                with contextlib.suppress(GitError):
                    self._run(["worktree", "prune"])

    # -- internals ------------------------------------------------------

    def _remote_ref(self, branch: str) -> str:
        return "{0}/{1}".format(self.remote, branch)

    def _run(self, args: Sequence[str]) -> str:
        cmd = [self.git] + list(args)
        log.debug("git %s", " ".join(args))
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitError("git {0} timed out".format(" ".join(args))) from exc
        except OSError as exc:
            raise GitError("could not run git: {0}".format(exc)) from exc

        if proc.returncode != 0:
            raise GitError(
                "git {0} failed ({1}): {2}".format(
                    " ".join(args),
                    proc.returncode,
                    proc.stderr.decode("utf-8", "replace").strip(),
                )
            )
        return proc.stdout.decode("utf-8", "replace")


def _parse_commits(out: str) -> List[Commit]:
    commits = []
    for record in out.split(_RECORD):
        record = record.strip("\n\r")
        if not record:
            continue
        fields = record.split(_FIELD)
        if len(fields) != 5:
            log.warning("skipping unparseable git log record %r", record)
            continue
        sha, email, name, when, subject = fields
        commits.append(
            Commit(
                sha=sha.strip(),
                author_email=email.strip(),
                author_name=name.strip(),
                committed_at=when.strip(),
                subject=subject.strip(),
            )
        )
    return commits
