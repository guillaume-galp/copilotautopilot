"""Process-wide network guard used by the self-hosted validation test."""

from __future__ import annotations

import os
import sys


NETWORK_EVENT_PREFIX = "socket."
NETWORK_BLOCK_EXIT = 97
NETWORK_BLOCK_MESSAGE = b"network-guard: blocked socket audit event\n"


def _deny_network(event: str, _arguments: tuple[object, ...]) -> None:
    if event.startswith(NETWORK_EVENT_PREFIX):
        os.write(2, NETWORK_BLOCK_MESSAGE)
        os._exit(NETWORK_BLOCK_EXIT)


sys.addaudithook(_deny_network)
