"""Reading requests from a repository other than the one being built.

The case this exists for: a customer permits cloning their repo but not
a branch or a commit from your account. Requests then live in a repo you
control, and theirs is only ever read.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from build_watcher.config import Config, ConfigError
from build_watcher.git_credentials import parse_owner_repo


def make_config(tmp: Path, **overrides) -> Config:
    data = dict(
        repo_url="git@github.com:customer-org/their-firmware.git",
        owner="customer-org",
        repo="their-firmware",
        trigger_branch="build-requests",
        root=tmp,
        allowed_committers=["*"],
    )
    data.update(overrides)
    return Config(**data)


class ParseOwnerRepoTest(unittest.TestCase):
    def test_ssh_url(self):
        self.assertEqual(
            parse_owner_repo("git@github.com:my-team/build-requests.git"),
            ("my-team", "build-requests"),
        )

    def test_https_url(self):
        self.assertEqual(
            parse_owner_repo("https://github.com/my-team/build-requests"),
            ("my-team", "build-requests"),
        )

    def test_https_url_with_git_suffix_and_slash(self):
        self.assertEqual(
            parse_owner_repo("https://github.com/my-team/build-requests.git/"),
            ("my-team", "build-requests"),
        )

    def test_unparseable(self):
        self.assertIsNone(parse_owner_repo("not-a-url"))


class SeparateTriggerRepoTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_defaults_to_watching_the_built_repo(self):
        config = make_config(self.tmp)
        self.assertFalse(config.watches_a_separate_repo)
        self.assertEqual(config.watch_url, config.repo_url)
        self.assertEqual(config.status_owner_repo(), ("customer-org", "their-firmware"))

    def test_separate_repo_is_watched_when_given(self):
        config = make_config(
            self.tmp,
            trigger_repo_url="git@github.com:my-team/build-requests.git",
        )
        self.assertTrue(config.watches_a_separate_repo)
        self.assertEqual(
            config.watch_url, "git@github.com:my-team/build-requests.git"
        )

    def test_statuses_follow_the_request_not_the_build(self):
        """Posting against the built repo would target a sha that is not
        in it -- the request commit only exists in the trigger repo.
        """
        config = make_config(
            self.tmp,
            trigger_repo_url="git@github.com:my-team/build-requests.git",
        )
        self.assertEqual(config.status_owner_repo(), ("my-team", "build-requests"))

    def test_same_url_spelled_out_is_not_treated_as_separate(self):
        url = "git@github.com:customer-org/their-firmware.git"
        config = make_config(self.tmp, trigger_repo_url=url)
        self.assertFalse(config.watches_a_separate_repo)
        self.assertEqual(config.status_owner_repo(), ("customer-org", "their-firmware"))

    def test_unparseable_trigger_url_is_refused_with_a_clear_message(self):
        config = make_config(self.tmp, trigger_repo_url="rubbish")
        with self.assertRaises(ConfigError) as ctx:
            config.status_owner_repo()
        self.assertIn("trigger_repo_url", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
