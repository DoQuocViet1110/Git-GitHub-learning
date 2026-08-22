from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from build_watcher.config import Config, ConfigError
from build_watcher.packager import Packager
from build_watcher.state import StateStore


class StateStoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "nested" / "state.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file_reads_as_first_run(self):
        self.assertIsNone(StateStore(self.path).last_sha())

    def test_round_trip(self):
        store = StateStore(self.path)
        store.advance("abc123")
        self.assertEqual(StateStore(self.path).last_sha(), "abc123")

    def test_corrupt_file_baselines_instead_of_replaying(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{not json", encoding="utf-8")
        self.assertIsNone(StateStore(self.path).last_sha())


class PackagerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.worktree = self.root / "wt"
        (self.worktree / "build" / "Debug").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_matches_returns_none(self):
        packager = Packager(["build/*/*.elf"], self.root / "out")
        self.assertIsNone(packager.package(self.worktree, "tag"))

    def test_zips_matches_with_relative_names(self):
        (self.worktree / "build" / "Debug" / "fw.elf").write_bytes(b"elf")
        (self.worktree / "build" / "Debug" / "fw.hex").write_bytes(b"hex")
        packager = Packager(["build/*/*.elf", "build/*/*.hex"], self.root / "out")

        archive = packager.package(self.worktree, "feature-a-abc123")

        self.assertIsNotNone(archive)
        self.assertEqual(archive.name, "feature-a-abc123.zip")
        with zipfile.ZipFile(archive) as zf:
            names = sorted(n.replace("\\", "/") for n in zf.namelist())
        self.assertEqual(names, ["build/Debug/fw.elf", "build/Debug/fw.hex"])

    def test_overlapping_globs_do_not_duplicate(self):
        (self.worktree / "build" / "Debug" / "fw.elf").write_bytes(b"elf")
        packager = Packager(["build/*/*.elf", "build/Debug/*.elf"], self.root / "out")
        archive = packager.package(self.worktree, "tag")
        with zipfile.ZipFile(archive) as zf:
            self.assertEqual(len(zf.namelist()), 1)


class ConfigLoadTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "config.json"

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, body: str):
        self.path.write_text(body, encoding="utf-8")
        return self.path

    def test_underscore_keys_are_comments(self):
        path = self.write(
            """{
              "_note": "JSON has no comments, so this stands in for one",
              "repo_url": "https://example.invalid/x.git",
              "owner": "acme", "repo": "fw", "trigger_branch": "build-requests",
              "allowed_committers": ["dev@example.com"]
            }"""
        )
        self.assertEqual(Config.load(path).owner, "acme")

    def test_real_typo_is_still_refused(self):
        path = self.write(
            """{
              "repo_url": "https://example.invalid/x.git",
              "owner": "acme", "repo": "fw", "trigger_branch": "build-requests",
              "allowed_committers": ["dev@example.com"],
              "poll_interval": 60
            }"""
        )
        with self.assertRaises(ConfigError) as ctx:
            Config.load(path)
        self.assertIn("poll_interval", str(ctx.exception))


class ConfigTest(unittest.TestCase):
    def base(self, **overrides):
        data = dict(
            repo_url="https://example.invalid/x.git",
            owner="acme",
            repo="firmware",
            trigger_branch="build-requests",
            allowed_committers=["dev@example.com"],
        )
        data.update(overrides)
        return data

    def test_empty_allowlist_is_refused(self):
        with self.assertRaises(ConfigError):
            Config(**self.base(allowed_committers=[]))

    def test_allowlist_is_case_insensitive(self):
        config = Config(**self.base(allowed_committers=["Dev@Example.com"]))
        self.assertTrue(config.allows("dev@example.com "))
        self.assertFalse(config.allows("other@example.com"))

    def test_too_fast_polling_is_refused(self):
        with self.assertRaises(ConfigError):
            Config(**self.base(poll_interval_seconds=1))

    def test_paths_default_under_root(self):
        config = Config(**self.base(root="/tmp/bw"))
        self.assertEqual(config.clone_dir, Path("/tmp/bw/repo"))
        self.assertEqual(config.state_file, Path("/tmp/bw/state.json"))

    def test_reporting_is_on_unless_turned_off(self):
        self.assertTrue(Config(**self.base()).report_to_github)
        self.assertFalse(Config(**self.base(report_to_github=False)).report_to_github)

    def test_short_root_has_no_warnings(self):
        self.assertEqual(Config(**self.base(root="C:/build-watcher")).warnings(), [])

    def test_long_root_warns_about_max_path(self):
        deep = "C:/" + "/".join("very-long-directory-name" for _ in range(5))
        warnings = Config(**self.base(root=deep)).warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("MAX_PATH", warnings[0])


if __name__ == "__main__":
    unittest.main()
