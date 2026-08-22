"""Watcher behaviour that the whole design hinges on: no request is lost."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from build_watcher.config import Config
from build_watcher.github_client import NullGitHubClient
from build_watcher.pipeline import BuildPipeline
from build_watcher.state import StateStore
from build_watcher.watcher import Watcher

from .fakes import FakeBuilder, FakePackager, FakeRepo


def make_config(tmp: Path, **overrides) -> Config:
    data = dict(
        repo_url="https://example.invalid/x.git",
        owner="acme",
        repo="firmware",
        trigger_branch="build-requests",
        root=tmp,
        allowed_committers=["dev@example.com"],
        poll_interval_seconds=5,
    )
    data.update(overrides)
    return Config(**data)


class WatcherTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.config = make_config(self.tmp)
        self.repo = FakeRepo(branches={"feature/a", "feature/b", "develop"})
        self.github = NullGitHubClient()
        self.builder = FakeBuilder()
        self.state = StateStore(self.config.state_file)
        self.pipeline = BuildPipeline(
            repo=self.repo,
            github=self.github,
            builder=self.builder,
            packager=FakePackager(),
            config=self.config,
        )
        self.watcher = Watcher(self.repo, self.state, self.pipeline, self.config)

    def tearDown(self):
        self._tmp.cleanup()

    def test_first_run_baselines_without_building(self):
        self.repo.push_request("aaa", "[Build] - [feature/a]")
        self.assertEqual(self.watcher.poll_once(), 0)
        self.assertEqual(self.builder.calls, [])
        self.assertEqual(self.state.last_sha(), "aaa")

    def test_builds_a_new_request(self):
        self.repo.push_request("aaa", "[Build] - [feature/a]")
        self.watcher.poll_once()  # baseline
        self.repo.push_request("bbb", "[Build] - [feature/b]")

        self.assertEqual(self.watcher.poll_once(), 1)
        self.assertEqual(len(self.builder.calls), 1)
        self.assertEqual(self.repo.worktrees_created, ["feature/b"])

    def test_two_pushes_between_polls_both_build(self):
        """The reason we walk commits instead of reading the file's head."""
        self.repo.push_request("aaa", "[Build] - [feature/a]")
        self.watcher.poll_once()  # baseline

        self.repo.push_request("bbb", "[Build] - [feature/a]")
        self.repo.push_request("ccc", "[Build] - [feature/b]")

        self.assertEqual(self.watcher.poll_once(), 2)
        self.assertEqual(self.repo.worktrees_created, ["feature/a", "feature/b"])

    def test_nothing_new_does_nothing(self):
        self.repo.push_request("aaa", "[Build] - [feature/a]")
        self.watcher.poll_once()
        self.assertEqual(self.watcher.poll_once(), 0)
        self.assertEqual(self.builder.calls, [])

    def test_state_survives_restart(self):
        self.repo.push_request("aaa", "[Build] - [feature/a]")
        self.watcher.poll_once()
        self.repo.push_request("bbb", "[Build] - [feature/b]")
        self.watcher.poll_once()

        fresh = Watcher(
            self.repo, StateStore(self.config.state_file), self.pipeline, self.config
        )
        self.assertEqual(fresh.poll_once(), 0)
        self.assertEqual(len(self.builder.calls), 1)

    def test_malformed_request_reports_failure_and_moves_on(self):
        self.repo.push_request("aaa", "[Build] - [feature/a]")
        self.watcher.poll_once()
        self.repo.push_request("bad", "[Build] oops")
        self.repo.push_request("ccc", "[Build] - [feature/b]")

        self.watcher.poll_once()
        states = [s[1] for s in self.github.statuses]
        self.assertIn("failure", states)
        self.assertEqual(self.repo.worktrees_created, ["feature/b"])


if __name__ == "__main__":
    unittest.main()
