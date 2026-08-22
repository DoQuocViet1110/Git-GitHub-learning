"""Report build status and publish artifacts, using only stdlib HTTP.

Two adapters live behind this interface: GitHubClient (real REST calls) and
NullGitHubClient (dry runs and tests). Nothing else in the tool knows about
tokens, retries, or the fact that publishing an artifact is three API calls.

Only ``Contents: read/write`` plus ``Commit statuses: read/write`` are
needed -- both are ordinary collaborator permissions, never repo Settings.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

STATE_PENDING = "pending"
STATE_SUCCESS = "success"
STATE_FAILURE = "failure"
STATE_ERROR = "error"

# GitHub truncates past 140; trim ourselves so the message stays sensible.
_MAX_DESCRIPTION = 138


class GitHubError(RuntimeError):
    """A GitHub API call failed after retries."""


class NullGitHubClient:
    """Adapter that records calls instead of making them.

    Used for dry runs, for tests, and for the no-token mode where builds
    run but nothing is reported back. ``label`` names which of those is
    happening so the log does not claim "dry-run" during a real build.
    """

    def __init__(self, label: str = "dry-run") -> None:
        self.label = label
        self.statuses = []
        self.artifacts = []

    def set_commit_status(
        self, sha: str, state: str, description: str, target_url: Optional[str] = None
    ) -> None:
        log.info("[%s] status %s on %s: %s", self.label, state, sha[:12], description)
        self.statuses.append((sha, state, description, target_url))

    def publish_artifact(
        self, tag: str, name: str, notes: str, asset: Path
    ) -> str:
        log.info("[%s] artifact kept locally: %s", self.label, asset)
        self.artifacts.append((tag, name, notes, asset))
        return ""


class GitHubClient:
    def __init__(
        self,
        owner: str,
        repo: str,
        token: str,
        status_context: str = "build-watcher",
        api_base: str = "https://api.github.com",
        upload_base: str = "https://uploads.github.com",
        timeout: int = 60,
        retries: int = 3,
    ) -> None:
        self.owner = owner
        self.repo = repo
        self.token = token
        self.status_context = status_context
        self.api_base = api_base.rstrip("/")
        self.upload_base = upload_base.rstrip("/")
        self.timeout = timeout
        self.retries = retries

    # -- interface ------------------------------------------------------

    def set_commit_status(
        self, sha: str, state: str, description: str, target_url: Optional[str] = None
    ) -> None:
        """Put a pass/fail marker on the commit that requested the build.

        This is what replaces the green tick Actions would have shown.
        Never raises: a reporting failure must not abort a build that
        already succeeded.
        """
        payload: Dict[str, Any] = {
            "state": state,
            "context": self.status_context,
            "description": description[:_MAX_DESCRIPTION],
        }
        if target_url:
            payload["target_url"] = target_url
        try:
            self._request(
                "POST",
                "{0}/repos/{1}/{2}/statuses/{3}".format(
                    self.api_base, self.owner, self.repo, sha
                ),
                payload,
            )
        except GitHubError as exc:
            log.error("could not set commit status on %s: %s", sha[:12], exc)

    def publish_artifact(self, tag: str, name: str, notes: str, asset: Path) -> str:
        """Upload ``asset`` to a release tagged ``tag``; return its page URL.

        Reuses the release when the tag already exists and replaces a
        same-named asset, so re-running a request is not an error.
        """
        release = self._ensure_release(tag, name, notes)
        release_id = release["id"]
        self._delete_existing_asset(release_id, asset.name)
        self._upload_asset(release_id, asset)
        return release.get("html_url", "")

    # -- internals ------------------------------------------------------

    def _ensure_release(self, tag: str, name: str, notes: str) -> Dict[str, Any]:
        try:
            return self._request(
                "POST",
                "{0}/repos/{1}/{2}/releases".format(
                    self.api_base, self.owner, self.repo
                ),
                {"tag_name": tag, "name": name, "body": notes, "prerelease": True},
            )
        except GitHubError as exc:
            if "already_exists" not in str(exc) and "422" not in str(exc):
                raise
            log.info("release %s exists; reusing it", tag)
            return self._request(
                "GET",
                "{0}/repos/{1}/{2}/releases/tags/{3}".format(
                    self.api_base, self.owner, self.repo, tag
                ),
            )

    def _delete_existing_asset(self, release_id: int, asset_name: str) -> None:
        release = self._request(
            "GET",
            "{0}/repos/{1}/{2}/releases/{3}".format(
                self.api_base, self.owner, self.repo, release_id
            ),
        )
        for asset in release.get("assets", []):
            if asset.get("name") == asset_name:
                log.info("replacing existing asset %s", asset_name)
                self._request(
                    "DELETE",
                    "{0}/repos/{1}/{2}/releases/assets/{3}".format(
                        self.api_base, self.owner, self.repo, asset["id"]
                    ),
                )

    def _upload_asset(self, release_id: int, asset: Path) -> None:
        url = "{0}/repos/{1}/{2}/releases/{3}/assets?name={4}".format(
            self.upload_base, self.owner, self.repo, release_id, asset.name
        )
        self._request(
            "POST", url, raw_body=asset.read_bytes(), content_type="application/zip"
        )

    def _request(
        self,
        method: str,
        url: str,
        payload: Optional[Dict[str, Any]] = None,
        raw_body: Optional[bytes] = None,
        content_type: str = "application/json",
    ) -> Dict[str, Any]:
        body = raw_body
        if body is None and payload is not None:
            body = json.dumps(payload).encode("utf-8")

        last_error = None
        for attempt in range(1, self.retries + 1):
            request = urllib.request.Request(url, data=body, method=method)
            request.add_header("Authorization", "Bearer {0}".format(self.token))
            request.add_header("Accept", "application/vnd.github+json")
            request.add_header("X-GitHub-Api-Version", "2022-11-28")
            request.add_header("User-Agent", "build-watcher")
            if body is not None:
                request.add_header("Content-Type", content_type)

            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                    text = resp.read().decode("utf-8", "replace")
                return json.loads(text) if text.strip() else {}
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")
                last_error = "HTTP {0}: {1}".format(exc.code, detail.strip())
                # 4xx other than rate limiting will not fix themselves.
                if exc.code < 500 and exc.code != 429:
                    raise GitHubError(last_error)
            except (urllib.error.URLError, OSError, ValueError) as exc:
                last_error = str(exc)

            if attempt < self.retries:
                delay = 2 ** attempt
                log.warning(
                    "%s %s failed (%s); retrying in %ss", method, url, last_error, delay
                )
                time.sleep(delay)

        raise GitHubError(last_error or "unknown error")
