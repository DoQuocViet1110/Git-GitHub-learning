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

_REQUIRED = ("repo_url", "owner", "repo", "trigger_branch")


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
    status_context: str = "build-watcher/local"
    api_base: str = "https://api.github.com"
    upload_base: str = "https://uploads.github.com"
    publish_artifacts: bool = True

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.clone_dir = Path(self.clone_dir or self.root / "repo")
        self.workspace_dir = Path(self.workspace_dir or self.root / "work")
        self.artifact_dir = Path(self.artifact_dir or self.root / "artifacts")
        self.log_dir = Path(self.log_dir or self.root / "logs")
        self.state_file = Path(self.state_file or self.root / "state.json")

        if self.poll_interval_seconds < 5:
            raise ConfigError("poll_interval_seconds must be at least 5")
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

        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        unknown = set(data) - known
        if unknown:
            raise ConfigError(
                "unknown config keys: {0}".format(", ".join(sorted(unknown)))
            )
        return cls(**data)

    def allows(self, committer_email: str) -> bool:
        """Whether this committer may trigger builds on this machine."""
        return committer_email.strip().lower() in {
            entry.strip().lower() for entry in self.allowed_committers
        }


def read_token(explicit: Optional[str] = None) -> str:
    """Token from an explicit value, else the environment.

    Never read from the repository, and never logged.
    """
    token = explicit or os.environ.get(TOKEN_ENV_VAR, "")
    if not token:
        raise ConfigError(
            "no GitHub token: set {0} for the account running this service".format(
                TOKEN_ENV_VAR
            )
        )
    return token
