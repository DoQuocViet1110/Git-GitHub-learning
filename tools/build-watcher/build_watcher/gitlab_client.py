"""Publish build artifacts to a GitLab project instead of GitHub.

The fallback for when a customer will not accept build output being
written into their own repository: watching and status reporting stay on
their GitHub repo, while the zip goes to a GitLab project the team
controls.

Uses GitLab's Generic Packages API rather than its Releases API: a
release needs a git tag in the GitLab project, and the code being built
does not live there -- only the artifact does.
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Package names accept a broad character set; anything outside it is
# replaced so a branch name like "feature/x" cannot break the URL.
_UNSAFE_IN_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class GitLabError(RuntimeError):
    """A GitLab API call failed after retries."""


def package_version_from(moment: Optional[datetime] = None) -> str:
    """A unique, semver-shaped version string for one build.

    GitLab validates generic package versions as semver, so the human
    identity of a build (branch, preset, sha) cannot live here -- it goes
    in the package name and file name instead. This encodes the build
    time, which is enough to keep successive uploads distinct, and avoids
    leading zeros because semver rejects them.
    """
    now = moment or datetime.now()
    return "{0}.{1}.{2}".format(
        now.year,
        now.month * 100 + now.day,
        now.hour * 10000 + now.minute * 100 + now.second,
    )


def safe_package_name(tag: str) -> str:
    cleaned = _UNSAFE_IN_NAME.sub("-", tag).strip("-")
    return cleaned or "build-artifact"


class GitLabClient:
    """Artifact publisher adapter for GitLab.

    Satisfies the same publish_artifact interface as GitHubClient, so the
    pipeline treats the two interchangeably. It deliberately implements
    nothing else: commit statuses belong on the host holding the commit.
    """

    def __init__(
        self,
        base_url: str,
        project_id: str,
        token: str,
        package_name: str = "",
        timeout: int = 120,
        retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.project_id = str(project_id)
        self.token = token
        self.package_name = package_name
        self.timeout = timeout
        self.retries = retries

    def publish_artifact(
        self,
        tag: str,
        name: str,
        notes: str,
        asset: Path,
        target_commitish: Optional[str] = None,
    ) -> str:
        """Upload ``asset`` as a generic package; return its download URL.

        ``notes`` and ``target_commitish`` have no home in the generic
        package API and are not silently discarded elsewhere -- they are
        already recorded in the commit status and the build log.
        """
        package = self.package_name or safe_package_name(tag)
        version = package_version_from()
        url = (
            "{0}/api/v4/projects/{1}/packages/generic/{2}/{3}/{4}".format(
                self.base_url,
                urllib.parse.quote(self.project_id, safe=""),
                urllib.parse.quote(package, safe=""),
                urllib.parse.quote(version, safe=""),
                urllib.parse.quote(asset.name, safe=""),
            )
        )
        self._request("PUT", url, asset.read_bytes())
        log.info("uploaded %s to GitLab package %s/%s", asset.name, package, version)
        return url

    def _request(self, method: str, url: str, body: bytes) -> dict:
        last_error = None
        for attempt in range(1, self.retries + 1):
            request = urllib.request.Request(url, data=body, method=method)
            request.add_header("PRIVATE-TOKEN", self.token)
            request.add_header("Content-Type", "application/octet-stream")
            request.add_header("User-Agent", "build-watcher")
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                    text = resp.read().decode("utf-8", "replace")
                return json.loads(text) if text.strip() else {}
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace").strip()
                last_error = "HTTP {0}: {1}".format(exc.code, detail)
                if exc.code < 500 and exc.code != 429:
                    raise GitLabError(last_error)
            except (urllib.error.URLError, OSError, ValueError) as exc:
                last_error = str(exc)

            if attempt < self.retries:
                delay = 2 ** attempt
                log.warning(
                    "GitLab upload failed (%s); retrying in %ss", last_error, delay
                )
                time.sleep(delay)

        raise GitLabError(last_error or "unknown error")
