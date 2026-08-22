"""Composition root: build a Watcher from a Config.

The only place that knows which concrete adapter fills each seam, which is
what lets the tests assemble the same pipeline out of fakes.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from .builder import Builder
from .config import Config, read_token
from .git_repo import GitRepo
from .github_client import GitHubClient, NullGitHubClient
from .packager import Packager
from .pipeline import BuildPipeline
from .state import StateStore
from .watcher import Watcher


def build_watcher(config: Config, dry_run: bool = False, token: Optional[str] = None) -> Watcher:
    repo = GitRepo.ensure_clone(
        url=config.repo_url,
        path=config.clone_dir,
        workspace=config.workspace_dir,
    )
    github = (
        NullGitHubClient()
        if dry_run
        else GitHubClient(
            owner=config.owner,
            repo=config.repo,
            token=read_token(token),
            status_context=config.status_context,
            api_base=config.api_base,
            upload_base=config.upload_base,
        )
    )
    pipeline = BuildPipeline(
        repo=repo,
        github=github,
        builder=Builder(
            script_name=config.build_script,
            log_dir=config.log_dir,
            timeout=config.build_timeout_seconds,
        ),
        packager=Packager(globs=config.artifact_globs, out_dir=config.artifact_dir),
        config=config,
    )
    return Watcher(
        repo=repo,
        state=StateStore(config.state_file),
        pipeline=pipeline,
        config=config,
    )


def setup_logging(log_dir: Path, verbose: bool = False) -> None:
    """Log to console and to a rotating file, since this runs unattended."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            str(log_dir / "build-watcher.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        ),
    ]
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=handlers,
    )
