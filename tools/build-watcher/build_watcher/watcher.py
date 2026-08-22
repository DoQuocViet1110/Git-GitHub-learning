"""Poll the trigger branch and hand each new request to the pipeline.

Two decisions worth knowing about:

* Requests are found by walking commits that touched the request file, not
  by reading the file's current contents. Two pushes between polls yield
  two builds instead of one, which is what makes polling interval a
  latency knob rather than a correctness risk.
* State advances after each request, so a crash resumes at the next
  unprocessed one.

Requests are processed one at a time in one thread; with a single build
machine there is nothing to gain from concurrency and a whole class of
checkout races to lose.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from .git_repo import GitError
from .models import BuildRequest
from .request_format import RequestFormatError, parse_build_request

log = logging.getLogger(__name__)

_MAX_BACKOFF = 600


class Watcher:
    def __init__(self, repo, state, pipeline, config) -> None:
        self.repo = repo
        self.state = state
        self.pipeline = pipeline
        self.config = config

    def poll_once(self) -> int:
        """Process every request pushed since last time; return how many."""
        self.repo.fetch()
        head = self.repo.remote_head(self.config.trigger_branch)
        last = self.state.last_sha()

        if last is None:
            # First run: adopt the current head rather than replay history,
            # which would rebuild every request ever made.
            log.info("first run; baseline set to %s", head[:12])
            self.state.advance(head)
            return 0

        if head == last:
            return 0

        commits = self.repo.commits_touching(
            self.config.trigger_branch,
            self.config.request_file,
            since=last,
            limit=self.config.max_requests_per_poll,
        )
        log.info("%d new request commit(s) since %s", len(commits), last[:12])

        processed = 0
        for commit in commits:
            self._handle(commit)
            self.state.advance(commit.sha)
            processed += 1

        # Commits that did not touch the request file are not requests, but
        # they must still not be re-examined next poll.
        self.state.advance(head)
        return processed

    def run_forever(self, stop: Optional[threading.Event] = None) -> None:
        stop = stop or threading.Event()
        backoff = self.config.poll_interval_seconds
        log.info(
            "watching %s on %s every %ss",
            self.config.request_file,
            self.config.trigger_branch,
            self.config.poll_interval_seconds,
        )
        while not stop.is_set():
            try:
                self.poll_once()
                backoff = self.config.poll_interval_seconds
            except GitError as exc:
                # Transient in practice (network, locked index): keep the
                # service alive and slow down instead of dying.
                log.error("poll failed: %s; backing off %ss", exc, backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)
            except Exception:  # noqa: BLE001 - the loop must outlive surprises
                log.exception("unexpected error in poll loop")
                backoff = min(backoff * 2, _MAX_BACKOFF)
            stop.wait(backoff)
        log.info("watcher stopped")

    def _handle(self, commit) -> None:
        try:
            text = self.repo.file_at(commit.sha, self.config.request_file)
        except GitError as exc:
            log.warning("cannot read request file at %s: %s", commit.short_sha, exc)
            return

        try:
            parsed = parse_build_request(text)
        except RequestFormatError as exc:
            log.warning("bad request at %s: %s", commit.short_sha, exc)
            self.pipeline.github.set_commit_status(
                commit.sha, "failure", "invalid request: {0}".format(exc)
            )
            return

        request = BuildRequest(
            commit=commit, branch=parsed.branch, preset=parsed.preset
        )
        log.info(
            "request %s from %s (%s)",
            request.tag,
            commit.author_email,
            commit.short_sha,
        )
        started = time.time()
        result = self.pipeline.process(request)
        log.info(
            "request %s -> %s (%.0fs): %s",
            request.tag,
            "ok" if result.ok else "FAILED",
            time.time() - started,
            result.description,
        )
