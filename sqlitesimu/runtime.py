from __future__ import annotations

import math
import queue
import threading
import time
import uuid
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from .db import SqliteStore
from .gateway import ApiGateway, ApiTransportError, SQLITESIMU_REAUTH_STATUSES
from .models import BatchItemRecord, BatchRecord, ExperimentRecord, RUN_TERMINAL_STATES, RuntimePolicy


_SIMULATION_SUCCESS_STATUSES = {"COMPLETE", "WARNING"}
_SIMULATION_FAILURE_STATUSES = {"ERROR", "FAILED", "FAILURE"}
_SIMULATION_RETRY_STATUSES = {"CANCELED", "CANCELLED"}


class SqliteSimuRuntime:
    def __init__(
        self,
        store: SqliteStore,
        gateway: ApiGateway,
        *,
        policy: RuntimePolicy | None = None,
        clock: Callable[[], float] = time.time,
        sleeper: Callable[[float], None] = time.sleep,
        worker_id: str | None = None,
    ) -> None:
        self.store = store
        self.gateway = gateway
        self.policy = policy or RuntimePolicy()
        self.clock = clock
        self.sleeper = sleeper
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex}"
        self._work_cursor = 0
        if self.policy.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.policy.default_retry_seconds <= 0 or self.policy.idle_sleep_seconds <= 0:
            raise ValueError("retry and idle sleep durations must be positive")
        if self.policy.resend_interval_seconds < 0:
            raise ValueError("resend interval must not be negative")
        if self.policy.lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        if self.policy.result_workers < 1:
            raise ValueError("result_workers must be at least 1")
        if self.policy.enrichment_workers < 1:
            raise ValueError("enrichment_workers must be at least 1")

    def run(
        self,
        run_id: str,
        *,
        max_runtime_seconds: float | None = None,
    ) -> dict[str, Any]:
        started = self.clock()
        self.store.acquire_run_lease(
            run_id,
            owner=self.worker_id,
            now=started,
            lease_seconds=self.policy.lease_seconds,
        )
        try:
            self.store.mark_run_running(run_id, now=started)
            self.store.recover_interrupted(run_id, now=started)
            if self.policy.concurrent:
                return self._run_concurrent(
                    run_id,
                    started=started,
                    max_runtime_seconds=max_runtime_seconds,
                )
            return self._run_sequential(
                run_id,
                started=started,
                max_runtime_seconds=max_runtime_seconds,
            )
        finally:
            self.store.release_run_lease(run_id, owner=self.worker_id)

    def _run_sequential(
        self,
        run_id: str,
        *,
        started: float,
        max_runtime_seconds: float | None,
    ) -> dict[str, Any]:
        refresh_at = started + self.policy.lease_seconds / 3
        while True:
            now = self.clock()
            if now >= refresh_at:
                self.store.renew_run_lease(
                    run_id,
                    owner=self.worker_id,
                    now=now,
                    lease_seconds=self.policy.lease_seconds,
                )
                refresh_at = now + self.policy.lease_seconds / 3
            summary = self.store.refresh_run_state(run_id, now=now)
            if summary["state"] in RUN_TERMINAL_STATES:
                return summary
            if max_runtime_seconds is not None and now - started >= max_runtime_seconds:
                return {**summary, "timed_out": True}
            if self._step(run_id, now=now):
                continue
            self.sleeper(self._idle_delay(run_id, now=now))

    def _run_concurrent(
        self,
        run_id: str,
        *,
        started: float,
        max_runtime_seconds: float | None,
    ) -> dict[str, Any]:
        stop = threading.Event()
        errors: queue.Queue[BaseException] = queue.Queue()
        threads: list[threading.Thread] = []

        def start_worker(name: str, target: Callable[[], None]) -> None:
            def guarded() -> None:
                try:
                    target()
                except BaseException as exc:
                    errors.put(exc)
                    stop.set()

            thread = threading.Thread(target=guarded, name=name, daemon=True)
            thread.start()
            threads.append(thread)

        refresh_at = started + self.policy.lease_seconds / 3
        timed_out = False
        worker_error: BaseException | None = None
        try:
            start_worker(
                "sqlitesimu-sender",
                lambda: self._simulation_lane(run_id, stop),
            )
            for index in range(self.policy.result_workers):
                start_worker(
                    f"sqlitesimu-result-{index + 1}",
                    lambda index=index: self._result_lane(run_id, stop, index=index),
                )
            for index in range(self.policy.enrichment_workers):
                start_worker(
                    f"sqlitesimu-enrichment-{index + 1}",
                    lambda index=index: self._enrichment_lane(run_id, stop, index=index),
                )

            while True:
                if not errors.empty():
                    worker_error = errors.get_nowait()
                    break
                now = self.clock()
                if now >= refresh_at:
                    self.store.renew_run_lease(
                        run_id,
                        owner=self.worker_id,
                        now=now,
                        lease_seconds=self.policy.lease_seconds,
                    )
                    refresh_at = now + self.policy.lease_seconds / 3
                summary = self.store.refresh_run_state(run_id, now=now)
                if summary["state"] in RUN_TERMINAL_STATES:
                    break
                if max_runtime_seconds is not None and now - started >= max_runtime_seconds:
                    timed_out = True
                    break
                stop.wait(self.policy.idle_sleep_seconds)
        finally:
            stop.set()
            for thread in threads:
                thread.join()

        if worker_error is None and not errors.empty():
            worker_error = errors.get_nowait()
        if worker_error is not None:
            raise RuntimeError(
                "sqlitesimu concurrent worker failed: "
                f"{type(worker_error).__name__}: {worker_error}"
            ) from worker_error
        summary = self.store.refresh_run_state(run_id, now=self.clock())
        return {**summary, **({"timed_out": True} if timed_out else {})}

    def _simulation_lane(self, run_id: str, stop: threading.Event) -> None:
        while not stop.is_set():
            if self._step_simulation(run_id, now=self.clock()):
                continue
            stop.wait(self.policy.idle_sleep_seconds)

    def _result_lane(
        self,
        run_id: str,
        stop: threading.Event,
        *,
        index: int,
    ) -> None:
        owner = f"{self.worker_id}:result:{index + 1}"
        prefer_parent = index % 2 == 0
        while not stop.is_set():
            now = self.clock()
            batch = None
            item = None
            if prefer_parent:
                batch = self.store.claim_poll_batch(run_id, owner=owner, now=now)
                if batch is None:
                    item = self.store.claim_child_item(run_id, owner=owner, now=now)
            else:
                item = self.store.claim_child_item(run_id, owner=owner, now=now)
                if item is None:
                    batch = self.store.claim_poll_batch(run_id, owner=owner, now=now)
            if batch is not None:
                self._poll_parent(batch, now=now)
                prefer_parent = False
                continue
            if item is not None:
                self._poll_child(item, now=now)
                prefer_parent = True
                continue
            stop.wait(self.policy.idle_sleep_seconds)

    def _enrichment_lane(
        self,
        run_id: str,
        stop: threading.Event,
        *,
        index: int,
    ) -> None:
        owner = f"{self.worker_id}:enrichment:{index + 1}"
        while not stop.is_set():
            experiment = self.store.claim_enrichment(
                run_id,
                owner=owner,
                now=self.clock(),
            )
            if experiment is not None:
                self._enrich(experiment, now=self.clock())
                continue
            stop.wait(self.policy.idle_sleep_seconds)

    def _step(self, run_id: str, *, now: float) -> bool:
        # The legacy sender and result collector ran independently. Rotate durable
        # queues so a large due poll set cannot starve enrichment or new simulations.
        workers = (
            self._step_parent_poll,
            self._step_child_poll,
            self._step_enrichment,
            self._step_simulation,
        )
        for offset in range(len(workers)):
            index = (self._work_cursor + offset) % len(workers)
            if workers[index](run_id, now=now):
                self._work_cursor = (index + 1) % len(workers)
                return True
        return False

    def _step_parent_poll(self, run_id: str, *, now: float) -> bool:
        batch = self.store.next_poll_batch(run_id, now=now)
        if batch:
            self._poll_parent(batch, now=now)
            return True
        return False

    def _step_child_poll(self, run_id: str, *, now: float) -> bool:
        item = self.store.next_child_item(run_id, now=now)
        if item:
            self._poll_child(item, now=now)
            return True
        return False

    def _step_enrichment(self, run_id: str, *, now: float) -> bool:
        experiment = self.store.next_enrichment(run_id, now=now)
        if experiment:
            self._enrich(experiment, now=now)
            return True
        return False

    def _step_simulation(self, run_id: str, *, now: float) -> bool:
        batch = self.store.next_simulate_batch(run_id, now=now)
        if batch:
            self._simulate(batch, now=now)
            return True
        return (
            self.store.create_next_batch(
                run_id,
                now=now,
                resend_interval_seconds=self.policy.resend_interval_seconds,
            )
            is not None
        )

    def _simulate(self, batch: BatchRecord, *, now: float) -> None:
        self.store.mark_simulate_started(batch.id, now=now)
        try:
            result = self.gateway.call("POST", "/simulations", json_body=batch.payload)
        except ApiTransportError as exc:
            self.store.fail_batch(
                batch.id,
                state="SIMULATE_UNKNOWN",
                error=str(exc),
                response=None,
                now=self.clock(),
            )
            return

        observed_at = self.clock()
        status_code = _status_code(result)
        if status_code == 201:
            location = _response(result).get("location")
            parent_id = _simulation_id(location)
            if isinstance(location, str) and parent_id:
                self.store.accept_simulation(
                    batch.id,
                    location=location,
                    parent_simulation_id=parent_id,
                    response=result,
                    not_before=observed_at + _retry_seconds(result, self.policy.default_retry_seconds),
                    now=observed_at,
                )
                return
            self.store.fail_batch(
                batch.id,
                state="SIMULATE_UNKNOWN",
                error="simulation_accepted_without_location",
                response=result,
                now=observed_at,
            )
            return

        if status_code in SQLITESIMU_REAUTH_STATUSES:
            retry_at = observed_at + _retry_seconds(result, self.policy.default_retry_seconds)
            if status_code == 429:
                self.store.set_runtime_float(
                    "simulation_request_not_before",
                    retry_at,
                    now=observed_at,
                )
            self.store.retry_simulate(
                batch.id,
                response=result,
                not_before=retry_at,
                error=_error_detail(
                    result,
                    f"session_recovery_exhausted_{status_code}",
                ),
                now=observed_at,
            )
            return

        if status_code in {400, 403, 404, 409, 422}:
            failure_state = "PERMANENT_FAILURE"
        else:
            failure_state = "SIMULATE_UNKNOWN"
        self.store.fail_batch(
            batch.id,
            state=failure_state,
            error=_error_detail(result, f"unexpected_simulate_status_{status_code}"),
            response=result,
            now=observed_at,
        )

    def _poll_parent(self, batch: BatchRecord, *, now: float) -> None:
        if not batch.parent_simulation_id:
            self.store.fail_batch(
                batch.id,
                state="PERMANENT_FAILURE",
                error="polling_batch_has_no_parent_simulation_id",
                response=None,
                now=now,
            )
            return
        try:
            result = self.gateway.call(
                "GET",
                "/simulations/{simulation_id}",
                path_vars={"simulation_id": batch.parent_simulation_id},
            )
        except ApiTransportError as exc:
            self._defer_or_fail_parent(batch, _transport_result(exc), now=self.clock())
            return

        observed_at = self.clock()
        status_code = _status_code(result)
        body = _body(result)
        status = _simulation_status(body)
        if status_code == 200 and status in _SIMULATION_SUCCESS_STATUSES:
            self._complete_parent(batch, body, result, now=observed_at)
            return
        if status_code == 200 and status in _SIMULATION_RETRY_STATUSES:
            self.store.retry_completed_batch(
                batch.id,
                error=_error_detail(result, f"parent_status_{status.lower()}"),
                response=result,
                not_before=observed_at + self.policy.default_retry_seconds,
                now=observed_at,
            )
            return
        if status_code == 200 and status in _SIMULATION_FAILURE_STATUSES:
            children = _child_ids(body)
            if children:
                self._complete_parent(batch, body, result, now=observed_at)
            else:
                self.store.retry_completed_batch(
                    batch.id,
                    error=_error_detail(result, f"parent_status_{status.lower()}"),
                    response=result,
                    not_before=observed_at + self.policy.default_retry_seconds,
                    now=observed_at,
                )
            return
        if status_code == 200:
            self.store.defer_parent_poll(
                batch.id,
                response=result,
                not_before=observed_at
                + _retry_seconds(
                    result,
                    self.policy.default_retry_seconds,
                    batch_size=_payload_size(batch.payload),
                ),
                status=status or None,
                increment_attempt=False,
                now=observed_at,
            )
            return
        if status_code in SQLITESIMU_REAUTH_STATUSES:
            self.store.defer_parent_poll(
                batch.id,
                response=result,
                not_before=observed_at
                + _retry_seconds(
                    result,
                    self.policy.default_retry_seconds,
                    batch_size=_payload_size(batch.payload),
                ),
                status=status or None,
                increment_attempt=False,
                now=observed_at,
            )
            return
        if _is_retryable_get(status_code):
            self._defer_or_fail_parent(batch, result, now=observed_at)
            return
        self.store.fail_batch(
            batch.id,
            state="PERMANENT_FAILURE",
            error=_error_detail(result, f"parent_poll_status_{status_code}"),
            response=result,
            now=observed_at,
        )

    def _complete_parent(
        self,
        batch: BatchRecord,
        body: dict[str, Any],
        result: dict[str, Any],
        *,
        now: float,
    ) -> None:
        try:
            self.store.complete_parent(
                batch.id,
                alpha_id=_alpha_id(body),
                child_ids=_child_ids(body),
                parent_status=_simulation_status(body) or "COMPLETE",
                response=result,
                now=now,
            )
        except ValueError as exc:
            self.store.fail_batch(
                batch.id,
                state="PERMANENT_FAILURE",
                error=f"invalid_parent_result: {exc}",
                response=result,
                now=now,
            )

    def _defer_or_fail_parent(
        self,
        batch: BatchRecord,
        result: dict[str, Any],
        *,
        now: float,
    ) -> None:
        # A progress URL is durable remote work. Transient GET failures must not
        # discard it; only an explicit remote terminal status consumes the attempt.
        self.store.defer_parent_poll(
            batch.id,
            response=result,
            not_before=now
            + _retry_seconds(
                result,
                self.policy.default_retry_seconds,
                batch_size=_payload_size(batch.payload),
            ),
            status=_simulation_status(_body(result)) or None,
            increment_attempt=True,
            now=now,
        )

    def _poll_child(self, item: BatchItemRecord, *, now: float) -> None:
        if not item.child_simulation_id:
            self.store.fail_child(
                item,
                error="child_poll_item_has_no_simulation_id",
                response=None,
                now=now,
            )
            return
        try:
            result = self.gateway.call(
                "GET",
                "/simulations/{simulation_id}",
                path_vars={"simulation_id": item.child_simulation_id},
            )
        except ApiTransportError as exc:
            self._defer_or_fail_child(item, _transport_result(exc), now=self.clock())
            return

        observed_at = self.clock()
        status_code = _status_code(result)
        body = _body(result)
        status = _simulation_status(body)
        alpha_id = _alpha_id(body)
        if status_code == 200 and status in _SIMULATION_SUCCESS_STATUSES:
            if alpha_id:
                self.store.complete_child(item, alpha_id=alpha_id, response=result, now=observed_at)
            else:
                self.store.fail_child(
                    item,
                    error="completed_child_has_no_alpha_id",
                    response=result,
                    now=observed_at,
                )
            return
        if status_code == 200 and status in _SIMULATION_RETRY_STATUSES:
            self.store.retry_child(
                item,
                error=_error_detail(result, f"child_status_{status.lower()}"),
                response=result,
                not_before=observed_at + self.policy.default_retry_seconds,
                now=observed_at,
            )
            return
        if status_code == 200 and status in _SIMULATION_FAILURE_STATUSES:
            error = _error_detail(result, f"child_status_{status.lower()}")
            if _is_retryable_simulation_error(error):
                self.store.retry_child(
                    item,
                    error=error,
                    response=result,
                    not_before=observed_at + self.policy.default_retry_seconds,
                    now=observed_at,
                )
            else:
                self.store.fail_child(
                    item,
                    error=error,
                    response=result,
                    now=observed_at,
                )
            return
        if status_code == 200:
            self.store.defer_child_poll(
                item,
                response=result,
                not_before=observed_at + _retry_seconds(result, self.policy.default_retry_seconds),
                increment_attempt=False,
            )
            return
        if status_code in SQLITESIMU_REAUTH_STATUSES:
            self.store.defer_child_poll(
                item,
                response=result,
                not_before=observed_at
                + _retry_seconds(result, self.policy.default_retry_seconds),
                increment_attempt=False,
            )
            return
        if _is_retryable_get(status_code):
            self._defer_or_fail_child(item, result, now=observed_at)
            return
        self.store.fail_child(
            item,
            error=_error_detail(result, f"child_poll_status_{status_code}"),
            response=result,
            now=observed_at,
        )

    def _defer_or_fail_child(
        self,
        item: BatchItemRecord,
        result: dict[str, Any],
        *,
        now: float,
    ) -> None:
        # Child simulation IDs follow the same durable polling contract as parent
        # progress URLs. Keep retry counts for diagnostics, not as a loss budget.
        self.store.defer_child_poll(
            item,
            response=result,
            not_before=now + _retry_seconds(result, self.policy.default_retry_seconds),
            increment_attempt=True,
        )

    def _enrich(self, experiment: ExperimentRecord, *, now: float) -> None:
        if not experiment.alpha_id:
            self.store.defer_enrichment(
                experiment,
                not_before=now,
                error="enrichment_has_no_alpha_id",
                terminal=True,
                now=now,
            )
            return
        path = "/alphas/{alpha_id}"
        if experiment.state == "ENRICH_PNL":
            path = "/alphas/{alpha_id}/recordsets/pnl"
        try:
            result = self.gateway.call(
                "GET",
                path,
                path_vars={"alpha_id": experiment.alpha_id},
            )
        except ApiTransportError as exc:
            self._defer_or_fail_enrichment(experiment, _transport_result(exc), now=self.clock())
            return

        observed_at = self.clock()
        if _status_code(result) != 200:
            status_code = _status_code(result)
            if status_code in SQLITESIMU_REAUTH_STATUSES:
                self.store.defer_enrichment(
                    experiment,
                    not_before=observed_at
                    + _retry_seconds(result, self.policy.default_retry_seconds),
                    error=_error_detail(
                        result,
                        f"session_recovery_exhausted_{status_code}",
                    ),
                    terminal=False,
                    increment_attempt=False,
                    now=observed_at,
                )
            elif _is_retryable_get(status_code):
                self._defer_or_fail_enrichment(experiment, result, now=observed_at)
            else:
                self.store.defer_enrichment(
                    experiment,
                    not_before=observed_at,
                    error=_error_detail(result, f"enrichment_status_{status_code}"),
                    terminal=True,
                    now=observed_at,
                )
            return
        body = _body(result)
        try:
            if experiment.state == "SIM_DONE":
                if not body:
                    raise ValueError("alpha detail body is empty")
                self.store.save_alpha_detail(experiment, body, response=result, now=observed_at)
            else:
                points = pnl_points(body)
                self.store.save_pnl(experiment, points, response=result, now=observed_at)
        except (TypeError, ValueError) as exc:
            self._defer_or_fail_enrichment(
                experiment,
                result,
                now=observed_at,
                detail=f"invalid_enrichment_result: {exc}",
            )

    def _defer_or_fail_enrichment(
        self,
        experiment: ExperimentRecord,
        result: dict[str, Any],
        *,
        now: float,
        detail: str | None = None,
    ) -> None:
        terminal = experiment.attempts + 1 >= self.policy.max_attempts
        self.store.defer_enrichment(
            experiment,
            not_before=now + _retry_seconds(result, self.policy.default_retry_seconds),
            error=detail or _error_detail(result, "enrichment_retry"),
            terminal=terminal,
            now=now,
        )

    def _idle_delay(self, run_id: str, *, now: float) -> float:
        due = self.store.next_due_time(run_id)
        if due is None or due <= now:
            return self.policy.idle_sleep_seconds
        return max(0.01, min(self.policy.idle_sleep_seconds, due - now))


def pnl_points(body: dict[str, Any]) -> list[tuple[str | None, float | None, float | None]]:
    records = body.get("records")
    if not isinstance(records, list):
        raise ValueError("PnL body must contain a records array")
    points: list[tuple[str | None, float | None, float | None]] = []
    previous: float | None = None
    for index, record in enumerate(records):
        if isinstance(record, (list, tuple)) and len(record) >= 2:
            date_value, raw_cumulative = record[0], record[1]
        elif isinstance(record, dict):
            date_value = record.get("date")
            raw_cumulative = record.get("pnl")
        else:
            raise ValueError(f"PnL record {index} has an unsupported shape")
        cumulative = _finite_float(raw_cumulative)
        if cumulative is None and previous is not None:
            cumulative = previous
        delta = None if cumulative is None or previous is None else cumulative - previous
        if cumulative is not None:
            previous = cumulative
        points.append((str(date_value) if date_value is not None else None, cumulative, delta))
    return points


def _response(result: dict[str, Any]) -> dict[str, Any]:
    response = result.get("response")
    return response if isinstance(response, dict) else {}


def _body(result: dict[str, Any]) -> dict[str, Any]:
    body = _response(result).get("body")
    return body if isinstance(body, dict) else {}


def _status_code(result: dict[str, Any]) -> int | None:
    value = _response(result).get("status_code")
    return int(value) if isinstance(value, int) else None


def _simulation_status(body: dict[str, Any]) -> str:
    value = body.get("status")
    return str(value).upper() if value is not None else ""


def _alpha_id(body: dict[str, Any]) -> str | None:
    alpha = body.get("alpha")
    if isinstance(alpha, dict):
        alpha = alpha.get("id")
    return str(alpha) if alpha else None


def _child_ids(body: dict[str, Any]) -> list[str]:
    children = body.get("children")
    if not isinstance(children, list):
        return []
    values: list[str] = []
    for child in children:
        value = child.get("id") if isinstance(child, dict) else child
        if value:
            values.append(str(value))
    return values


def _simulation_id(location: Any) -> str | None:
    if not isinstance(location, str) or not location.strip():
        return None
    path = urlparse(location).path.rstrip("/")
    value = path.rsplit("/", 1)[-1]
    return value or None


def _retry_seconds(
    result: dict[str, Any],
    default: float,
    *,
    batch_size: int | None = None,
) -> float:
    raw = _response(result).get("retry_after")
    try:
        seconds = float(raw) if raw not in {None, ""} else float(default)
    except (TypeError, ValueError):
        seconds = float(default)
    progress = _body(result).get("progress")
    try:
        numeric_progress = float(progress)
    except (TypeError, ValueError):
        numeric_progress = None
    if (
        numeric_progress is not None
        and abs(numeric_progress - 0.35) <= 0.01
        and batch_size is not None
    ):
        seconds *= max(1.0, batch_size / 2)
    return max(0.01, seconds)


def _payload_size(payload: Any) -> int:
    return len(payload) if isinstance(payload, list) else 1


def _is_retryable_get(status_code: int | None) -> bool:
    return status_code is None or status_code in {404, 408, 425, 429} or (
        status_code is not None and 500 <= status_code < 600
    )


def _is_retryable_simulation_error(error: str) -> bool:
    return error.startswith(
        (
            "There was an error while running",
            "Your simulation probably took too much resource.",
            "Your simulation has been running too long.",
        )
    )


def _error_detail(result: dict[str, Any], fallback: str) -> str:
    body = _response(result).get("body")
    if isinstance(body, dict):
        for key in ("detail", "message", "error"):
            value = body.get(key)
            if value:
                return str(value)
    detail = result.get("detail")
    return str(detail) if detail else fallback


def _transport_result(exc: ApiTransportError) -> dict[str, Any]:
    return {
        "ok": False,
        "error_type": type(exc).__name__,
        "detail": str(exc),
        "response": {"status_code": None, "body": None, "retry_after": None},
    }


def _finite_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


__all__ = ["SqliteSimuRuntime", "pnl_points"]
