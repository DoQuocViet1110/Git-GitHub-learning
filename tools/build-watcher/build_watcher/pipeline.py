"""Turn one build request into a status and (on success) a published zip.

The single rule this module enforces: every request reaches exactly one
terminal status -- success or failure -- whatever goes wrong on the way.
Silent drops are what make a pull-based CI impossible to trust.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .config import Config
from .github_client import STATE_FAILURE, STATE_PENDING, STATE_SUCCESS
from .models import BuildRequest

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RequestResult:
    ok: bool
    description: str
    artifact_url: Optional[str] = None


class BuildPipeline:
    def __init__(self, repo, github, builder, packager, config: Config) -> None:
        self.repo = repo
        self.github = github
        self.builder = builder
        self.packager = packager
        self.config = config

    def process(self, request: BuildRequest) -> RequestResult:
        """Run ``request`` end to end and report it. Never raises."""
        sha = request.commit.sha
        try:
            result = self._process(request)
        except Exception as exc:  # noqa: BLE001 - a crash must still be reported
            log.exception("unhandled error while processing %s", request.tag)
            result = RequestResult(False, "internal error: {0}".format(exc))

        self.github.set_commit_status(
            sha,
            STATE_SUCCESS if result.ok else STATE_FAILURE,
            result.description,
            result.artifact_url,
        )
        return result

    def _process(self, request: BuildRequest) -> RequestResult:
        rejection = self._reject(request)
        if rejection:
            log.warning("rejected %s: %s", request.tag, rejection)
            return RequestResult(False, rejection)

        self.github.set_commit_status(
            request.commit.sha,
            STATE_PENDING,
            "building {0}".format(request.branch),
        )

        with self.repo.worktree(request.branch) as worktree:
            outcome = self.builder.run(worktree, request.preset, request.tag)
            if not outcome.succeeded:
                return RequestResult(
                    False,
                    "{0} (exit {1}, {2:.0f}s)".format(
                        outcome.message, outcome.exit_code, outcome.duration_seconds
                    ),
                )

            archive = self.packager.package(worktree, request.tag)

        if archive is None:
            return RequestResult(False, "build succeeded but produced no artifacts")

        if not self.config.publish_artifacts:
            return RequestResult(
                True, "built in {0:.0f}s (upload disabled)".format(
                    outcome.duration_seconds
                )
            )

        url = self.github.publish_artifact(
            tag="build/{0}".format(request.tag),
            name=request.tag,
            notes=self._notes(request, outcome),
            asset=archive,
        )
        return RequestResult(
            True, "built in {0:.0f}s".format(outcome.duration_seconds), url
        )

    def _reject(self, request: BuildRequest) -> Optional[str]:
        """Why this request must not run, or None if it may."""
        if not self.config.allows(request.commit.author_email):
            return "requester {0} is not on this machine's allowlist".format(
                request.commit.author_email
            )
        if request.preset and request.preset not in self.config.allowed_presets:
            return "preset {0!r} is not one of {1}".format(
                request.preset, ", ".join(self.config.allowed_presets)
            )
        if not self.repo.ref_exists(request.branch):
            return "branch {0!r} does not exist on the remote".format(request.branch)
        return None

    def _notes(self, request: BuildRequest, outcome) -> str:
        return "\n".join(
            [
                "Branch: `{0}`".format(request.branch),
                "Preset: `{0}`".format(request.preset or "all"),
                "Requested by: {0} <{1}>".format(
                    request.commit.author_name, request.commit.author_email
                ),
                "Request commit: `{0}`".format(request.commit.sha),
                "Build duration: {0:.0f}s".format(outcome.duration_seconds),
                "",
                "Built automatically by build-watcher on the local build machine.",
            ]
        )
