#!/usr/bin/env python3
"""Shared runtime error type for desktop command helpers."""


class DesktopRuntimeError(RuntimeError):
    """Structured command failure that the CLI wrapper can render as JSON."""

    def __init__(self, message, platform_name=None, hint=None, details=None):
        super().__init__(message)
        self.message = message
        self.platform_name = platform_name
        self.hint = hint
        self.details = details
