"""fill_credential shells out to a real `git`; these fake it with a tiny
stand-in script so the tests exercise parsing/timeout/failure handling
without depending on any machine's actual credential store.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from build_watcher.git_credentials import fill_credential, host_from_url


class HostFromUrlTest(unittest.TestCase):
    def test_https_url(self):
        self.assertEqual(
            host_from_url("https://github.com/acme/firmware.git"), "github.com"
        )

    def test_enterprise_host(self):
        self.assertEqual(
            host_from_url("https://git.acme.internal/team/firmware.git"),
            "git.acme.internal",
        )


class FillCredentialTest(unittest.TestCase):
    """Points fill_credential at a fake `git` (a Python script standing in
    for `git credential fill`), one per platform since Windows has no
    shebang.
    """

    def make_git_stub(self, body: str) -> str:
        if os.name == "nt":
            script = tempfile.NamedTemporaryFile(
                suffix=".py", delete=False, mode="w", encoding="utf-8"
            )
            script.write(body)
            script.close()
            self.addCleanup(os.unlink, script.name)

            stub = tempfile.NamedTemporaryFile(
                suffix=".bat", delete=False, mode="w", encoding="utf-8"
            )
            stub.write('@"{0}" "{1}" %*\n'.format(sys.executable, script.name))
            stub.close()
            self.addCleanup(os.unlink, stub.name)
            return stub.name

        stub = tempfile.NamedTemporaryFile(
            suffix="", delete=False, mode="w", encoding="utf-8"
        )
        stub.write("#!{0}\n{1}\n".format(sys.executable, body))
        stub.close()
        os.chmod(stub.name, os.stat(stub.name).st_mode | stat.S_IEXEC)
        self.addCleanup(os.unlink, stub.name)
        return stub.name

    def test_extracts_password_from_fill_output(self):
        stub = self.make_git_stub(
            "import sys\n"
            "sys.stdout.write('username=me\\npassword=secret-token-value\\n')\n"
        )
        token = fill_credential("github.com", git_executable=stub)
        self.assertEqual(token, "secret-token-value")

    def test_ignores_lines_other_than_password(self):
        stub = self.make_git_stub(
            "import sys\n"
            "sys.stdout.write('protocol=https\\nusername=me\\npassword=abc123\\nurl=x\\n')\n"
        )
        self.assertEqual(fill_credential("github.com", git_executable=stub), "abc123")

    def test_no_credential_cached_returns_none(self):
        """A helper with nothing to fill exits non-zero; must not raise."""
        stub = self.make_git_stub("import sys\nsys.exit(1)\n")
        self.assertIsNone(fill_credential("github.com", git_executable=stub))

    def test_output_with_no_password_line_returns_none(self):
        stub = self.make_git_stub(
            "import sys\nsys.stdout.write('username=me\\n')\n"
        )
        self.assertIsNone(fill_credential("github.com", git_executable=stub))

    def test_missing_executable_returns_none_not_raise(self):
        token = fill_credential("github.com", git_executable="/no/such/git-binary-xyz")
        self.assertIsNone(token)


class FillCredentialTimeoutTest(unittest.TestCase):
    """A hanging real helper is exercised through a mock, not a live
    subprocess: on Windows, killing a batch/cmd-wrapped process on timeout
    does not kill its grandchildren, so a genuinely hung process leaves the
    stdout pipe open and subprocess.run's post-timeout communicate() blocks
    for the full duration anyway -- that is a Windows process-tree
    limitation to design around in production, not something to reproduce
    in a unit test.
    """

    def test_timeout_returns_none_not_raise(self):
        with mock.patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=1),
        ):
            token = fill_credential("github.com", git_executable="git", timeout=1)
        self.assertIsNone(token)


if __name__ == "__main__":
    unittest.main()
