"""Background worker: N threads polling the queue and dispatching to registered handlers."""

from __future__ import annotations

import logging
import threading
import time
import traceback
from typing import Callable

from ..core.models import Job
from .queue import JobQueue

log = logging.getLogger(__name__)

Handler = Callable[[Job, "ProgressFn"], dict]
ProgressFn = Callable[[int, str], None]


class Worker:
    def __init__(self, queue: JobQueue, threads: int = 2, poll_interval: float = 0.5):
        self.queue = queue
        self.threads = threads
        self.poll_interval = poll_interval
        self._handlers: dict[str, Handler] = {}
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    def register(self, kind: str, handler: Handler) -> None:
        self._handlers[kind] = handler

    def start(self) -> None:
        self._stop.clear()
        for i in range(self.threads):
            t = threading.Thread(target=self._loop, name=f"ka-worker-{i}", daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        for t in self._threads:
            t.join(timeout)
        self._threads.clear()

    def run_one(self) -> bool:
        """Claim and run a single job synchronously. Returns False if the queue was empty."""
        job = self.queue.claim(list(self._handlers))
        if job is None:
            return False
        self._run(job)
        return True

    def _run(self, job: Job) -> None:
        handler = self._handlers.get(job.kind)
        if handler is None:
            self.queue.fail(job.id, f"no handler for kind '{job.kind}'")
            return
        progress: ProgressFn = lambda pct, msg="": self.queue.progress(job.id, pct, msg)
        try:
            result = handler(job, progress)
            self.queue.complete(job.id, result)
        except Exception as e:  # handler errors must never kill the worker thread
            log.warning("job %s (%s) failed: %s", job.id, job.kind, e)
            self.queue.fail(job.id, f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                if not self.run_one():
                    self._stop.wait(self.poll_interval)
            except Exception:
                log.exception("worker loop error")
                self._stop.wait(self.poll_interval)
