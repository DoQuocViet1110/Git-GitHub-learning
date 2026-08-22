"""read_token's fallback order: explicit -> env var -> git credential."""

from __future__ import annotations

import unittest
from unittest import mock

from build_watcher.config import ConfigError, read_token


class ReadTokenTest(unittest.TestCase):
    def test_explicit_wins(self):
        with mock.patch.dict("os.environ", {"BUILD_WATCHER_GITHUB_TOKEN": "env-val"}):
            self.assertEqual(read_token(explicit="explicit-val"), "explicit-val")

    def test_falls_back_to_env_var(self):
        with mock.patch.dict("os.environ", {"BUILD_WATCHER_GITHUB_TOKEN": "env-val"}):
            self.assertEqual(read_token(), "env-val")

    def test_falls_back_to_git_credential_when_host_given(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch(
                "build_watcher.git_credentials.fill_credential",
                return_value="borrowed-token",
            ):
                self.assertEqual(
                    read_token(host="github.com"), "borrowed-token"
                )

    def test_no_source_at_all_raises_actionable_error(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch(
                "build_watcher.git_credentials.fill_credential", return_value=None
            ):
                with self.assertRaises(ConfigError) as ctx:
                    read_token(host="github.com")
                self.assertIn("BUILD_WATCHER_GITHUB_TOKEN", str(ctx.exception))

    def test_no_host_skips_git_credential_lookup(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ConfigError):
                read_token()


if __name__ == "__main__":
    unittest.main()
