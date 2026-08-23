"""Drive GitLabClient over real HTTP against a stand-in GitLab.

test_gitlab_client covers URL construction with the transport mocked out;
this exercises the transport itself -- headers, request body, status-code
handling and retries -- without needing a real GitLab account. The server
binds to an ephemeral port on the loopback interface, so nothing here
touches the network.
"""

from __future__ import annotations

import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from build_watcher.gitlab_client import GitLabClient, GitLabError


class _Recorder(BaseHTTPRequestHandler):
    """Records the request, then replies with whatever the test wants."""

    received = None
    status_sequence = [201]

    def do_PUT(self):  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        length = int(self.headers.get("Content-Length", 0))
        type(self).received = {
            "path": self.path,
            "body": self.rfile.read(length),
            "token": self.headers.get("PRIVATE-TOKEN"),
            "content_type": self.headers.get("Content-Type"),
            "user_agent": self.headers.get("User-Agent"),
        }
        status = type(self).status_sequence.pop(0)
        payload = b'{"message":"boom"}' if status >= 400 else b"{}"
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        pass  # keep the test output clean


class GitLabHttpTest(unittest.TestCase):
    def setUp(self):
        _Recorder.received = None
        _Recorder.status_sequence = [201]
        self.server = HTTPServer(("127.0.0.1", 0), _Recorder)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = "http://127.0.0.1:{0}".format(self.server.server_port)

        self._tmp = tempfile.TemporaryDirectory()
        self.asset = Path(self._tmp.name) / "firmware.zip"
        self.asset.write_bytes(b"PK\x03\x04 pretend zip")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self._tmp.cleanup()

    def client(self, **kwargs) -> GitLabClient:
        return GitLabClient(
            base_url=self.base_url, project_id="4242", token="glpat-secret", **kwargs
        )

    def test_uploads_the_file_with_the_expected_request(self):
        url = self.client().publish_artifact(
            tag="feature/x-Debug-abc123", name="n", notes="", asset=self.asset
        )

        got = _Recorder.received
        self.assertIsNotNone(got, "server never received a request")
        self.assertEqual(got["body"], b"PK\x03\x04 pretend zip")
        self.assertEqual(got["token"], "glpat-secret")
        self.assertEqual(got["content_type"], "application/octet-stream")
        self.assertEqual(got["user_agent"], "build-watcher")
        self.assertTrue(got["path"].startswith("/api/v4/projects/4242/packages/generic/"))
        self.assertTrue(got["path"].endswith("/firmware.zip"))
        self.assertTrue(url.endswith(got["path"]))

    def test_wrong_project_id_fails_fast_without_retrying(self):
        """A 404 will not fix itself, so retrying only delays the error."""
        _Recorder.status_sequence = [404]
        with self.assertRaises(GitLabError) as ctx:
            self.client().publish_artifact("t", "n", "", self.asset)
        self.assertIn("404", str(ctx.exception))
        self.assertEqual(_Recorder.status_sequence, [], "should not have retried")

    def test_bad_token_fails_fast(self):
        _Recorder.status_sequence = [401]
        with self.assertRaises(GitLabError) as ctx:
            self.client().publish_artifact("t", "n", "", self.asset)
        self.assertIn("401", str(ctx.exception))

    def test_server_error_is_retried_then_succeeds(self):
        _Recorder.status_sequence = [500, 201]
        url = self.client(retries=2).publish_artifact("t", "n", "", self.asset)
        self.assertTrue(url)
        self.assertEqual(_Recorder.status_sequence, [], "both responses consumed")


if __name__ == "__main__":
    unittest.main()
