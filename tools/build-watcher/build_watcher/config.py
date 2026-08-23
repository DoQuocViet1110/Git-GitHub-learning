"""Load and validate the build machine's configuration.

Every policy decision the tool makes -- which script runs, who may trigger
a build, which presets exist -- is answered from here, i.e. from the build
machine, never from repository content.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

TOKEN_ENV_VAR = "BUILD_WATCHER_GITHUB_TOKEN"
GITLAB_TOKEN_ENV_VAR = "BUILD_WATCHER_GITLAB_TOKEN"

_ARTIFACT_TARGETS = ("github", "gitlab", "local")

# A literal "*" in allowed_committers means "trust anyone who can push to
# the trigger branch" -- a deliberate, visible opt-out of the allowlist,
# not the same as leaving the check out of the code entirely.
TRUST_ALL_COMMITTERS = "*"

_REQUIRED = ("repo_url", "owner", "repo", "trigger_branch")

# Builds run inside <workspace>/wt-<12 hex>/, and a deep C project adds
# another ~120 characters below that before Windows' 260-char MAX_PATH
# bites -- as a nested object file, not as a clear error. Keep the root
# short (C:\build-watcher) and this never comes up.
_MAX_SAFE_WORKSPACE_LEN = 60


class ConfigError(ValueError):
    """The configuration file is missing or contradicts itself."""


@dataclass
class Config:
    # what to watch
    repo_url: str
    owner: str
    repo: str
    trigger_branch: str
    request_file: str = "Build_Infor.txt"
    poll_interval_seconds: int = 60

    # where things live on this machine
    root: Path = Path("C:/build-watcher")
    clone_dir: Optional[Path] = None
    workspace_dir: Optional[Path] = None
    artifact_dir: Optional[Path] = None
    log_dir: Optional[Path] = None
    state_file: Optional[Path] = None

    # how to build
    build_script: str = "build.bat"
    build_timeout_seconds: int = 3600
    artifact_globs: List[str] = field(
        default_factory=lambda: [
            "build/*/*.elf",
            "build/*/*.hex",
            "build/*/*.bin",
            "build/*/*.map",
        ]
    )

    # policy
    allowed_committers: List[str] = field(default_factory=list)
    allowed_presets: List[str] = field(default_factory=lambda: ["Debug", "Release"])
    max_requests_per_poll: int = 20

    # reporting
    #
    # report_to_github False is the no-token mode: builds still run and
    # zips still land in artifact_dir, but nothing is sent back. Useful
    # while a token is still being arranged, and on machines where one is
    # never going to be allowed.
    report_to_github: bool = True
    status_context: str = "build-watcher/local"
    api_base: str = "https://api.github.com"
    upload_base: str = "https://uploads.github.com"
    publish_artifacts: bool = True

    # Where the zip goes. "github" puts it on the watched repo; "gitlab"
    # sends it to a project the team owns, for customers who will not
    # accept build output in their repository; "local" keeps it only in
    # artifact_dir. Commit statuses are unaffected -- they can only be
    # attached where the commit lives.
    artifact_target: str = "github"
    gitlab_url: str = "https://gitlab.com"
    gitlab_project_id: str = ""
    gitlab_package_name: str = ""

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.clone_dir = Path(self.clone_dir or self.root / "repo")
        self.workspace_dir = Path(self.workspace_dir or self.root / "work")
        self.artifact_dir = Path(self.artifact_dir or self.root / "artifacts")
        self.log_dir = Path(self.log_dir or self.root / "logs")
        self.state_file = Path(self.state_file or self.root / "state.json")

        if self.poll_interval_seconds < 5:
            raise ConfigError("poll_interval_seconds must be at least 5")
        if self.artifact_target not in _ARTIFACT_TARGETS:
            raise ConfigError(
                "artifact_target must be one of {0}, got {1!r}".format(
                    ", ".join(sorted(_ARTIFACT_TARGETS)), self.artifact_target
                )
            )
        if self.artifact_target == "gitlab" and not self.gitlab_project_id:
            raise ConfigError(
                "artifact_target is 'gitlab' but gitlab_project_id is empty; "
                "find it on the GitLab project's main page, under the project "
                "name (a number such as 12345678)"
            )
        if not self.allowed_committers:
            raise ConfigError(
                "allowed_committers must list at least one email; an empty list "
                "would let anyone who can push to the trigger branch run builds "
                "on this machine"
            )

    @classmethod
    def load(cls, path: Path) -> "Config":
        path = Path(path)
        try:
            data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ConfigError("cannot read config {0}: {1}".format(path, exc))
        except ValueError as exc:
            raise ConfigError("config {0} is not valid JSON: {1}".format(path, exc))

        missing = [key for key in _REQUIRED if not data.get(key)]
        if missing:
            raise ConfigError("config is missing: {0}".format(", ".join(missing)))

        # JSON has no comments, so keys starting with "_" are treated as
        # notes for whoever edits this file next and dropped here.
        data = {k: v for k, v in data.items() if not k.startswith("_")}

        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        unknown = set(data) - known
        if unknown:
            raise ConfigError(
                "unknown config keys: {0}".format(", ".join(sorted(unknown)))
            )
        return cls(**data)

    def warnings(self) -> List[str]:
        """Setup problems that are not fatal but will bite later.

        Returned rather than logged so the caller decides how loudly to
        say them; `check` prints them, `run` logs them once at startup.
        """
        found = []
        workspace = str(self.workspace_dir)
        if len(workspace) > _MAX_SAFE_WORKSPACE_LEN:
            found.append(
                "workspace path is {0} characters ({1}); deep builds can hit "
                "Windows' 260-char MAX_PATH and fail with confusing "
                "'cannot open ... for writing' errors. Prefer a short root "
                "such as C:\\build-watcher".format(len(workspace), workspace)
            )
        return found

    def allows(self, committer_email: str) -> bool:
        """Whether this committer may trigger builds on this machine."""
        if TRUST_ALL_COMMITTERS in self.allowed_committers:
            return True
        return committer_email.strip().lower() in {
            entry.strip().lower() for entry in self.allowed_committers
        }


def read_token(
    explicit: Optional[str] = None,
    host: Optional[str] = None,
    ssh_remote: bool = False,
) -> str:
    """Resolve a token: explicit value, then the environment, then git.

    The third source -- borrowing whatever credential `git push` already
    uses via git_credentials.fill_credential -- is what lets this run
    without anyone visiting a Settings page: it reuses auth the operator
    already needed to set up regardless. See git_credentials.py.
    """
    token = explicit or os.environ.get(TOKEN_ENV_VAR, "")
    if token:
        return token

    if host:
        from . import git_credentials

        borrowed = git_credentials.fill_credential(host)
        if borrowed:
            return borrowed

    if ssh_remote:
        # SSH authenticates the git transport only; GitHub's REST API does
        # not accept SSH keys, and SSH auth leaves nothing in the HTTPS
        # credential store to borrow. A token is unavoidable here.
        raise ConfigError(
            "this repository is cloned over SSH, and SSH keys cannot be used "
            "for GitHub's API (releases and commit statuses). Either set {0} "
            "to a personal access token, or set \"report_to_github\": false "
            "to build without reporting back".format(TOKEN_ENV_VAR)
        )

    raise ConfigError(
        "no GitHub token: set {0}, or make sure `git push` already works "
        "on this machine for the repository's host (the token is then "
        "borrowed from git's own credential helper -- no separate token "
        "needed)".format(TOKEN_ENV_VAR)
    )


def read_gitlab_token(gitlab_url: str, explicit: Optional[str] = None) -> str:
    """Token for GitLab uploads: explicit, environment, then git.

    Same order as read_token, and for the same reason: a machine that
    already pushes to this GitLab over HTTPS has a credential worth
    reusing instead of asking the operator to mint another token.
    """
    token = explicit or os.environ.get(GITLAB_TOKEN_ENV_VAR, "")
    if token:
        return token

    from . import git_credentials

    host = git_credentials.host_from_url(gitlab_url)
    if host:
        borrowed = git_credentials.fill_credential(host)
        if borrowed:
            return borrowed

    raise ConfigError(
        "no GitLab token: set {0} to a GitLab personal access token with the "
        "'api' scope (Preferences -> Access Tokens on your GitLab), or make "
        "sure `git push` over HTTPS already works on this machine for "
        "{1}".format(GITLAB_TOKEN_ENV_VAR, host or gitlab_url)
    )
