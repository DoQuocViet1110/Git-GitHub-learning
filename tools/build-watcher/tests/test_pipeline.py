"""Every request must end at exactly one terminal status."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from build_watcher.github_client import NullGitHubClient
from build_watcher.models import BuildRequest, Commit
from build_watcher.pipeline import BuildPipeline

from .fakes import FakeBuilder, FakePackager, FakeRepo
from .test_watcher import make_config


def request(branch="feature/a", preset=None, email="dev@example.com") -> BuildRequest:
    return BuildRequest(
        commit=Commit("sha123456789abc", email, "Dev", "2026-08-22T10:00:00+07:00", "req"),
        branch=branch,
        preset=preset,
    )


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.config = make_config(Path(self._tmp.name))
        self.repo = FakeRepo(branches={"feature/a"})
        self.github = NullGitHubClient()
        self.builder = FakeBuilder()
        self.packager = FakePackager()

    def tearDown(self):
        self._tmp.cleanup()

    def pipeline(self) -> BuildPipeline:
        return BuildPipeline(
            self.repo, self.github, self.builder, self.packager, self.config
        )

    def terminal_states(self):
        return [s[1] for s in self.github.statuses if s[1] != "pending"]

    def test_success_publishes_and_reports(self):
        result = self.pipeline().process(request())
        self.assertTrue(result.ok)
        self.assertEqual(self.terminal_states(), ["success"])
        self.assertEqual(len(self.github.artifacts), 1)

    def test_release_is_pinned_to_the_built_commit_not_the_request_commit(self):
        """Regression test: publish_artifact used to omit target_commitish,
        so GitHub silently tagged the release against the repo's default
        branch instead of the code that was actually compiled -- caught by
        inspecting a real release on GitHub, where the tag's commit didn't
        match the "Request commit" printed in the release body.
        """
        self.repo.branch_heads["feature/a"] = "actual-built-sha-1234567890"
        self.pipeline().process(request(branch="feature/a"))

        self.assertEqual(len(self.github.artifacts), 1)
        _tag, _name, _notes, _asset, target_commitish = self.github.artifacts[0]
        self.assertEqual(target_commitish, "actual-built-sha-1234567890")
        self.assertNotEqual(target_commitish, request().commit.sha)

    def test_unknown_requester_never_reaches_the_builder(self):
        result = self.pipeline().process(request(email="stranger@evil.test"))
        self.assertFalse(result.ok)
        self.assertIn("allowlist", result.description)
        self.assertEqual(self.builder.calls, [])
        self.assertEqual(self.terminal_states(), ["failure"])

    def test_unknown_preset_rejected(self):
        result = self.pipeline().process(request(preset="Evil"))
        self.assertFalse(result.ok)
        self.assertEqual(self.builder.calls, [])
        self.assertEqual(self.terminal_states(), ["failure"])

    def test_missing_branch_rejected(self):
        result = self.pipeline().process(request(branch="feature/ghost"))
        self.assertFalse(result.ok)
        self.assertIn("does not exist", result.description)
        self.assertEqual(self.terminal_states(), ["failure"])

    def test_build_failure_reported_and_nothing_published(self):
        self.builder = FakeBuilder(succeeded=False, message="build script failed")
        result = self.pipeline().process(request())
        self.assertFalse(result.ok)
        self.assertEqual(self.terminal_states(), ["failure"])
        self.assertEqual(self.github.artifacts, [])

    def test_empty_artifact_set_is_a_failure(self):
        self.packager = FakePackager(archive=None)
        result = self.pipeline().process(request())
        self.assertFalse(result.ok)
        self.assertIn("no artifacts", result.description)
        self.assertEqual(self.github.artifacts, [])

    def test_unexpected_error_still_produces_a_status(self):
        class Exploding:
            def run(self, *_args):
                raise RuntimeError("disk on fire")

        self.builder = Exploding()
        result = self.pipeline().process(request())
        self.assertFalse(result.ok)
        self.assertIn("internal error", result.description)
        self.assertEqual(self.terminal_states(), ["failure"])

    def test_publishing_can_be_disabled(self):
        self.config.publish_artifacts = False
        result = self.pipeline().process(request())
        self.assertTrue(result.ok)
        self.assertEqual(self.github.artifacts, [])


if __name__ == "__main__":
    unittest.main()
