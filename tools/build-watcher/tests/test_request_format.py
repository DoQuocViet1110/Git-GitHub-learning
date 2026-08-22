from __future__ import annotations

import unittest

from build_watcher.request_format import RequestFormatError, parse_build_request


class ParseBuildRequest(unittest.TestCase):
    def test_branch_only(self):
        parsed = parse_build_request("[Build] - [feature/my-branch]")
        self.assertEqual(parsed.branch, "feature/my-branch")
        self.assertIsNone(parsed.preset)

    def test_branch_and_preset(self):
        parsed = parse_build_request("[Build] - [develop] - [Debug]")
        self.assertEqual(parsed.branch, "develop")
        self.assertEqual(parsed.preset, "Debug")

    def test_tolerates_spacing_and_case(self):
        parsed = parse_build_request("  [ build ]  -  [ develop ]  ")
        self.assertEqual(parsed.branch, "develop")

    def test_last_request_line_wins(self):
        text = "\n".join(
            [
                "# history below, newest last",
                "[Build] - [old-branch]",
                "[Build] - [new-branch]",
            ]
        )
        self.assertEqual(parse_build_request(text).branch, "new-branch")

    def test_comments_and_blanks_ignored(self):
        text = "\n".join(["", "# [Build] - [commented-out]", "[Build] - [real]", ""])
        self.assertEqual(parse_build_request(text).branch, "real")

    def test_no_request_line(self):
        with self.assertRaises(RequestFormatError):
            parse_build_request("nothing to see here")

    def test_malformed_line_is_an_error_not_a_silent_skip(self):
        with self.assertRaises(RequestFormatError):
            parse_build_request("[Build] feature/my-branch")

    def test_empty_branch(self):
        with self.assertRaises(RequestFormatError):
            parse_build_request("[Build] - []")

    def test_rejects_option_injection(self):
        for branch in ("--upload-pack=evil", "-x", "a b", "a;b", "..", "a/../b", "x/"):
            with self.subTest(branch=branch):
                with self.assertRaises(RequestFormatError):
                    parse_build_request("[Build] - [{0}]".format(branch))

    def test_rejects_unsafe_preset(self):
        with self.assertRaises(RequestFormatError):
            parse_build_request("[Build] - [develop] - [Debug && evil]")


if __name__ == "__main__":
    unittest.main()
