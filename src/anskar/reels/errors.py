"""Errors for the autonomous Instagram Reels pipeline."""

from __future__ import annotations


class ReelError(Exception):
    def __init__(self, message: str, *, kind: str = "error") -> None:
        super().__init__(message)
        self.kind = kind
