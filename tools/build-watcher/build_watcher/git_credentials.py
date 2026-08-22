"""Borrow whatever credential `git push` already uses -- no token to create.

`git credential fill` is git's own plumbing command: it asks whatever
credential helper is configured (Git Credential Manager, the OS keychain,
a plain store) for a credential, the same way `git push` does internally.
On a machine where push/pull already work, this returns something usable
without the operator ever visiting a Settings page: no PAT to generate, no
SSH key to register. It works identically on this machine and on a fresh
one, because it rides on setup the operator already needed regardless.

The tradeoff: this trusts whatever scope that credential already has. If
it lacks write access to Releases or commit statuses, calls fail loudly
(403) rather than silently -- see github_client.GitHubError -- and the
fallback is config.report_to_github = false.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from typing import Optional
from urllib.parse import urlparse

log = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 15


_SSH_URL = re.compile(r"^(?:ssh://)?(?:[^@/]+@)(?P<host>[^:/]+)[:/]")


def host_from_url(url: str) -> str:
    """Extract the hostname git-credential needs from a repo URL.

    Handles SSH remotes (git@github.com:owner/repo.git) too, since a repo
    can be cloned over SSH while its API is still reached over HTTPS. The
    credential lookup will usually come back empty for such a host -- SSH
    auth leaves nothing in the HTTPS credential store -- but the caller
    reports that as "no token" rather than crashing on an unparsed URL.
    """
    url = url.strip()
    match = _SSH_URL.match(url)
    if match:
        return match.group("host")
    parsed = urlparse(url)
    return parsed.hostname or url


def is_ssh_url(url: str) -> bool:
    """Whether ``url`` is an SSH remote, which cannot yield an API token."""
    return bool(_SSH_URL.match(url.strip()))


def fill_credential(
    host: str,
    protocol: str = "https",
    git_executable: str = "git",
    timeout: int = _TIMEOUT_SECONDS,
) -> Optional[str]:
    """Return the password/token git already has stored for ``host``.

    None if no credential is cached and nothing can be filled in
    non-interactively. GIT_TERMINAL_PROMPT=0 is essential here: without it,
    a helper with nothing cached can block waiting for console input,
    which would hang the poll loop instead of failing fast.
    """
    request = "protocol={0}\nhost={1}\n\n".format(protocol, host)
    env = dict(os.environ)
    # GIT_TERMINAL_PROMPT only silences git's own console prompt. Git
    # Credential Manager has a separate interactivity switch and, left
    # alone, may open a browser for OAuth when nothing is cached yet --
    # exactly wrong for a service with no one watching the screen. Both
    # must be set so a machine with no cached credential fails fast
    # instead of hanging until `timeout` (or the browser) gives up.
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"

    try:
        proc = subprocess.run(
            [git_executable, "credential", "fill"],
            input=request.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        log.debug("git credential fill for %s did not complete: %s", host, exc)
        return None

    if proc.returncode != 0:
        log.debug(
            "git credential fill for %s exited %s: %s",
            host,
            proc.returncode,
            proc.stderr.decode("utf-8", "replace").strip(),
        )
        return None

    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith("password="):
            return line[len("password=") :]
    return None
