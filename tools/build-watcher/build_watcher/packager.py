"""Collect build outputs into one zip.

Which files count is config, not code: the globs are relative to the
worktree so the same packager serves any project whose build script leaves
artifacts behind.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import List, Optional, Sequence

log = logging.getLogger(__name__)


class Packager:
    def __init__(self, globs: Sequence[str], out_dir: Path) -> None:
        self.globs = list(globs)
        self.out_dir = Path(out_dir)

    def package(self, worktree: Path, tag: str) -> Optional[Path]:
        """Zip everything matching the globs; None when nothing matched.

        None is the honest answer for "the script exited 0 but produced no
        artifacts" -- the pipeline turns that into a failed status instead
        of publishing an empty archive.
        """
        worktree = Path(worktree)
        files = self._collect(worktree)
        if not files:
            log.warning("no artifacts matched %s under %s", self.globs, worktree)
            return None

        self.out_dir.mkdir(parents=True, exist_ok=True)
        archive = self.out_dir / "{0}.zip".format(tag)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in files:
                zf.write(path, arcname=str(path.relative_to(worktree)))
        log.info("packaged %d file(s) into %s", len(files), archive)
        return archive

    def _collect(self, worktree: Path) -> List[Path]:
        found = []
        seen = set()
        for pattern in self.globs:
            for path in sorted(worktree.glob(pattern)):
                if path.is_file() and path not in seen:
                    seen.add(path)
                    found.append(path)
        return found
