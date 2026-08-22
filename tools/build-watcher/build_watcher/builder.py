"""Run the build script inside a checked-out worktree.

The script name comes from this machine's config, never from the request --
see request_format for why. Failure is returned as a BuildOutcome rather
than raised, so the pipeline can report it like any other result.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from .models import BuildOutcome

log = logging.getLogger(__name__)


class Builder:
    def __init__(self, script_name: str, log_dir: Path, timeout: int = 3600) -> None:
        self.script_name = script_name
        self.log_dir = Path(log_dir)
        self.timeout = timeout

    def run(self, worktree: Path, preset: Optional[str], tag: str) -> BuildOutcome:
        """Build ``worktree``; the log is always written, pass or fail."""
        script = Path(worktree) / self.script_name
        if not script.is_file():
            return BuildOutcome(
                succeeded=False,
                exit_code=-1,
                message="{0} not found on this branch".format(self.script_name),
                log_path=None,
                duration_seconds=0.0,
            )

        self.log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.log_dir / "{0}.log".format(tag)
        command = self._command(script, preset)
        log.info("building %s: %s", tag, " ".join(command))

        started = time.time()
        try:
            with open(log_path, "wb") as sink:
                proc = subprocess.run(
                    command,
                    cwd=str(worktree),
                    stdout=sink,
                    stderr=subprocess.STDOUT,
                    timeout=self.timeout,
                )
            exit_code = proc.returncode
            message = "build finished" if exit_code == 0 else "build script failed"
        except subprocess.TimeoutExpired:
            exit_code = -2
            message = "build exceeded {0}s and was killed".format(self.timeout)
        except OSError as exc:
            exit_code = -3
            message = "could not start build script: {0}".format(exc)

        duration = time.time() - started
        return BuildOutcome(
            succeeded=exit_code == 0,
            exit_code=exit_code,
            message=message,
            log_path=log_path,
            duration_seconds=duration,
        )

    def _command(self, script: Path, preset: Optional[str]):
        """Invoke .bat through cmd.exe explicitly rather than via shell=True."""
        if os.name == "nt" and script.suffix.lower() in (".bat", ".cmd"):
            command = [os.environ.get("COMSPEC", "cmd.exe"), "/c", str(script)]
        else:
            command = [str(script)]
        if preset:
            command.append(preset)
        return command
