"""In-memory run store for the prototype.

A real deployment would persist this in a database; for a three-venue
prototype an in-process store keyed by run id is sufficient and keeps the
service stateless to set up.
"""
from __future__ import annotations

import uuid
from threading import Lock

from app.schemas import PipelineRunResult


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, PipelineRunResult] = {}
        self._lock = Lock()

    def create(self, result: PipelineRunResult) -> str:
        run_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._runs[run_id] = result
        return run_id

    def get(self, run_id: str) -> PipelineRunResult | None:
        return self._runs.get(run_id)

    def update(self, run_id: str, result: PipelineRunResult) -> None:
        with self._lock:
            self._runs[run_id] = result

    def list_ids(self) -> list[str]:
        return list(self._runs.keys())


run_store = RunStore()
