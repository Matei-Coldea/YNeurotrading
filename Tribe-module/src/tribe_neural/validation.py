"""Input/output validation and custom exceptions."""

from __future__ import annotations


class PipelineError(Exception):
    """Raised when a pipeline step fails."""

    def __init__(self, step: int, detail: str) -> None:
        self.step = step
        self.detail = detail
        super().__init__(f"Step {step}: {detail}")
