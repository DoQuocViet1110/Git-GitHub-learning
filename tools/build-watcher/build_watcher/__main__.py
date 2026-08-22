"""Command line entry point: python -m build_watcher --config config.json <cmd>."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading

from .app import build_watcher, setup_logging
from .config import Config, ConfigError, read_token

log = logging.getLogger("build_watcher")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="build_watcher", description=__doc__)
    parser.add_argument("--config", required=True, help="path to config.json")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="build, but do not touch GitHub (no statuses, no releases)",
    )
    parser.add_argument("--verbose", action="store_true", help="debug logging")
    parser.add_argument(
        "command",
        choices=["run", "once", "check"],
        help="run: poll forever; once: a single poll; check: validate setup",
    )
    args = parser.parse_args(argv)

    try:
        config = Config.load(args.config)
    except ConfigError as exc:
        print("config error: {0}".format(exc), file=sys.stderr)
        return 2

    setup_logging(config.log_dir, args.verbose)

    if args.command == "check":
        return _check(config, args.dry_run)

    try:
        watcher = build_watcher(config, dry_run=args.dry_run)
    except ConfigError as exc:
        log.error("%s", exc)
        return 2

    if args.command == "once":
        processed = watcher.poll_once()
        log.info("processed %d request(s)", processed)
        return 0

    stop = threading.Event()

    def _handle_signal(signum, _frame):
        log.info("signal %s received; finishing current work", signum)
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handle_signal)

    watcher.run_forever(stop)
    return 0


def _check(config: Config, dry_run: bool) -> int:
    """Validate config, credentials and remote access without building."""
    problems = []

    if not dry_run:
        try:
            read_token()
        except ConfigError as exc:
            problems.append(str(exc))

    try:
        watcher = build_watcher(config, dry_run=True)
        watcher.repo.fetch()
        head = watcher.repo.remote_head(config.trigger_branch)
        log.info("trigger branch %s is at %s", config.trigger_branch, head[:12])
        try:
            watcher.repo.file_at(head, config.request_file)
            log.info("request file %s found", config.request_file)
        except Exception as exc:  # noqa: BLE001
            problems.append(
                "request file {0} not readable on {1}: {2}".format(
                    config.request_file, config.trigger_branch, exc
                )
            )
    except Exception as exc:  # noqa: BLE001
        problems.append("cannot reach the repository: {0}".format(exc))

    log.info("allowlisted requesters: %s", ", ".join(config.allowed_committers))
    log.info("build script: %s", config.build_script)

    if problems:
        for problem in problems:
            log.error("%s", problem)
        return 1
    log.info("check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
