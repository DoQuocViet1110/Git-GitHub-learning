"""GitLab publishing: URL shape, and the semver constraint it works around."""

from __future__ import annotations

import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from build_watcher.gitlab_client import (
    GitLabClient,
    package_version_from,
    safe_package_name,
)

# What GitLab accepts for a generic package version: three numeric parts,
# none with a leading zero.
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class PackageVersionTest(unittest.TestCase):
    def test_looks_like_semver(self):
        """GitLab rejects a version that is not semver-shaped, which is why
        the build's real identity lives in the package name instead.
        """
        self.assertRegex(package_version_from(), _SEMVER)

    def test_no_leading_zeros_for_early_dates(self):
        """A January date would produce "0102" as a naive minor part, which
        semver rejects; the encoding must avoid that.
        """
        version = package_version_from(datetime(2026, 1, 2, 3, 4, 5))
        self.assertRegex(version, _SEMVER)

    def test_distinct_builds_get_distinct_versions(self):
        first = package_version_from(datetime(2026, 8, 23, 1, 0, 0))
        second = package_version_from(datetime(2026, 8, 23, 1, 0, 1))
        self.assertNotEqual(first, second)


class SafePackageNameTest(unittest.TestCase):
    def test_slashes_replaced(self):
        self.assertEqual(
            safe_package_name("feature/my-branch-Debug-abc123"),
            "feature-my-branch-Debug-abc123",
        )

    def test_never_returns_empty(self):
        self.assertEqual(safe_package_name("///"), "build-artifact")


class PublishArtifactTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.asset = Path(self._tmp.name) / "firmware.zip"
        self.asset.write_bytes(b"zip-bytes")

    def tearDown(self):
        self._tmp.cleanup()

    def test_uploads_to_generic_packages_endpoint(self):
        client = GitLabClient(
            base_url="https://gitlab.example.com/",
            project_id="12345",
            token="glpat-x",
        )
        with mock.patch.object(client, "_request", return_value={}) as request:
            url = client.publish_artifact(
                tag="feature/x-Debug-abc",
                name="n",
                notes="notes",
                asset=self.asset,
                target_commitish="abc",
            )

        method, called_url, body = request.call_args[0]
        self.assertEqual(method, "PUT")
        self.assertEqual(body, b"zip-bytes")
        self.assertIn("/api/v4/projects/12345/packages/generic/", called_url)
        self.assertTrue(called_url.endswith("/firmware.zip"))
        # Trailing slash on base_url must not produce a double slash.
        self.assertNotIn("//api/v4", called_url)
        self.assertEqual(url, called_url)

    def test_branch_slashes_do_not_break_the_url_path(self):
        client = GitLabClient("https://gitlab.example.com", "1", "t")
        with mock.patch.object(client, "_request", return_value={}) as request:
            client.publish_artifact("feature/a/b", "n", "", self.asset)
        called_url = request.call_args[0][1]
        after_generic = called_url.split("/packages/generic/", 1)[1]
        # package / version / filename -- exactly three segments.
        self.assertEqual(len(after_generic.split("/")), 3)

    def test_explicit_package_name_overrides_the_tag(self):
        client = GitLabClient(
            "https://gitlab.example.com", "1", "t", package_name="stm32-firmware"
        )
        with mock.patch.object(client, "_request", return_value={}) as request:
            client.publish_artifact("feature/x", "n", "", self.asset)
        self.assertIn("/generic/stm32-firmware/", request.call_args[0][1])


if __name__ == "__main__":
    unittest.main()
