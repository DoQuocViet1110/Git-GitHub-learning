"""Parse the request file that lives on the trigger branch.

Format, one request per line::

    [Build] - [feature/my-branch]
    [Build] - [feature/my-branch] - [Debug]

Blank lines and ``#`` comments are ignored. When a file holds several
request lines the **last** one wins, so the file can keep a readable
history above the active request.

Deliberately absent: any way to name the script to execute. The build
script is fixed by the build machine's own config, never by repository
content -- the request file is attacker-controlled input as far as this
machine is concerned.
"""

from __future__ import annotations

import re

from .models import ParsedRequest

MARKER = "[Build]"

# Must stay at least as permissive as _LINE, or a line _LINE would accept
# gets dropped as "not a request" before it is ever parsed.
_MARKER_HINT = re.compile(r"\[\s*build\s*\]", re.IGNORECASE)

_LINE = re.compile(
    r"^\s*\[\s*Build\s*\]\s*-\s*\[(?P<branch>[^\]]*)\]"
    r"(?:\s*-\s*\[(?P<preset>[^\]]*)\])?\s*$",
    re.IGNORECASE,
)

# Git refs allow more than this, but everything outside this set is either a
# quoting hazard or an option-injection hazard once it reaches the git CLI.
_BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")

_PRESET = re.compile(r"^[A-Za-z0-9._-]+$")


class RequestFormatError(ValueError):
    """The file contains a build request, but it is not usable."""


def parse_build_request(text: str) -> ParsedRequest:
    """Return the active request in ``text``.

    Raises RequestFormatError if no usable request line is present, so the
    caller always ends up with either a valid request or a reportable
    failure -- never a silently ignored typo.
    """
    candidates = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not _MARKER_HINT.search(line):
            continue
        candidates.append(line)

    if not candidates:
        raise RequestFormatError(
            "no '[Build] - [branch]' line found in the request file"
        )

    line = candidates[-1]
    match = _LINE.match(line)
    if not match:
        raise RequestFormatError(
            "malformed request line {0!r}; expected '[Build] - [branch]' "
            "or '[Build] - [branch] - [preset]'".format(line)
        )

    branch = match.group("branch").strip()
    if not branch:
        raise RequestFormatError("branch name is empty")
    if not _BRANCH.match(branch) or ".." in branch or branch.endswith("/"):
        raise RequestFormatError("unsafe branch name {0!r}".format(branch))

    preset_raw = match.group("preset")
    preset = preset_raw.strip() if preset_raw is not None else None
    if preset is not None:
        if not preset:
            raise RequestFormatError("preset is empty; omit the field instead")
        if not _PRESET.match(preset):
            raise RequestFormatError("unsafe preset {0!r}".format(preset))

    return ParsedRequest(branch=branch, preset=preset)
