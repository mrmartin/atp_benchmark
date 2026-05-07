"""Per-attempt budget enforcement.

Generalists (Claude Code, DeepSeek V4 Pro):
    200 K tokens, 30 min wall clock, 40 tool calls.

Goedel-V2:
    k = 16 whole-proof samples, 4 096 tokens per sample, no wall clock cap.
    Tracked separately because Goedel doesn't run an agent loop.
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class GeneralistBudget:
    max_tokens: int = 200_000
    max_seconds: int = 1_800  # 30 min
    max_tool_calls: int = 40

    def __post_init__(self) -> None:
        self.start = time.monotonic()
        self.tokens_used = 0
        self.tool_calls = 0

    def remaining_seconds(self) -> float:
        return max(0.0, self.max_seconds - (time.monotonic() - self.start))

    def can_continue(self) -> tuple[bool, str | None]:
        if self.tokens_used >= self.max_tokens:
            return False, f"token cap {self.max_tokens} reached"
        if self.tool_calls >= self.max_tool_calls:
            return False, f"tool-call cap {self.max_tool_calls} reached"
        if self.remaining_seconds() <= 0:
            return False, f"wall-clock cap {self.max_seconds}s reached"
        return True, None

    def add_tokens(self, n: int) -> None:
        self.tokens_used += max(0, n)

    def add_tool_call(self) -> None:
        self.tool_calls += 1

    def snapshot(self) -> dict:
        elapsed = time.monotonic() - self.start
        return {
            "tokens_used": self.tokens_used,
            "tool_calls": self.tool_calls,
            "wall_seconds": round(elapsed, 2),
        }


@dataclass
class GoedelBudget:
    """Per-sample budget for Goedel-V2: 4 096 tokens, no wall cap."""

    max_tokens_per_sample: int = 4_096
    samples: int = 16
