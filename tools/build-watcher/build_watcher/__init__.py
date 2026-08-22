"""Poll a GitHub branch for build requests and build them on this machine.

Designed for repositories where we cannot reach Settings (no self-hosted
Actions runner, no webhooks). Everything here works with plain git access
plus a token that can write contents/statuses.
"""

__version__ = "0.1.0"
