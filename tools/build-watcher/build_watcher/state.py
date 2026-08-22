"""Remember which commit was processed last, across restarts.

Written atomically and advanced after each request rather than after each
batch, so a crash mid-batch resumes at the next unprocessed request instead
of replaying builds that already ran.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def last_sha(self) -> Optional[str]:
        """SHA processed last, or None on a first run / unreadable state."""
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            # Treating corruption as "first run" re-baselines rather than
            # replaying history; losing a request beats a rebuild storm.
            log.warning("state file %s unreadable (%s); starting fresh", self.path, exc)
            return None
        sha = data.get("last_sha")
        return sha if isinstance(sha, str) and sha else None

    def advance(self, sha: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as fh:
                json.dump({"last_sha": sha}, fh)
            os.replace(tmp, str(self.path))
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        log.debug("state advanced to %s", sha[:12])
