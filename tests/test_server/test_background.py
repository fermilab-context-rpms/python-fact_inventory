"""Tests for AsyncBackgroundJobPlugin lifecycle and job execution.

Tests verify plugin initialization, lifespan management, and job execution
reliability. These tests ensure background jobs start correctly, survive
transient failures, and shut down cleanly.

Design Notes:
- Plugin construction tests validate config constraints
- Lifespan tests verify task lifecycle (create, run, cancel)
- Execution tests check resilience (exception handling, recovery)
- Task names are verified for monitoring/debugging
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock, MagicMock

import pytest

from fact_inventory.server.background import AsyncBackgroundJobPlugin

DEFAULT_INTERVAL_SECONDS = 60
JobCallback = Callable[[], Awaitable[int]]


def run_immediately(plugin: AsyncBackgroundJobPlugin) -> AsyncBackgroundJobPlugin:
    """Force a background plugin to execute without waiting."""
    plugin._interval = 0
    plugin._jitter = 0
    return plugin


def build_plugin(
    *,
    job_callback: JobCallback | None = None,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    jitter_seconds: int = 0,
    name: str = "background-job",
) -> AsyncBackgroundJobPlugin:
    """Build AsyncBackgroundJobPlugin instances with sensible test defaults."""
    callback = AsyncMock(return_value=0) if job_callback is None else job_callback
    return AsyncBackgroundJobPlugin(
        job_callback=callback,
        interval_seconds=interval_seconds,
        jitter_seconds=jitter_seconds,
        name=name,
    )


def tasks_named(name: str) -> list[asyncio.Task[object]]:
    """Return currently running tasks with the given name."""
    result: list[asyncio.Task[object]] = []
    for task in asyncio.all_tasks():
        if task.get_name() == name:
            result.append(task)
    return result


@pytest.fixture
def mock_app() -> MagicMock:
    """Provide a mock Litestar app for lifespan testing."""
    return MagicMock()


def test_initialization_valid_config_succeeds() -> None:
    """Plugin construction succeeds with valid interval >= 60 seconds."""
    build_plugin(name="test")


def test_initialization_rejects_interval_below_60() -> None:
    """Plugin rejects interval_seconds < 60 with ValueError."""
    with pytest.raises(ValueError):
        build_plugin(interval_seconds=30)


def test_initialization_rejects_negative_jitter() -> None:
    """Plugin rejects jitter_seconds < 0 with ValueError."""
    with pytest.raises(ValueError):
        build_plugin(jitter_seconds=-1)


def test_initialization_job_exception_does_not_prevent_construction() -> None:
    """Plugin construction succeeds even if job callback raises exceptions.

    Exceptions in the callback are caught during execution (_loop), not construction.
    This allows plugin to be instantiated with problematic callbacks for testing.
    """
    failing = AsyncMock(side_effect=RuntimeError("boom"))
    AsyncBackgroundJobPlugin(
        job_callback=failing, interval_seconds=DEFAULT_INTERVAL_SECONDS
    )


def test_initialization_jitter_value_stored() -> None:
    """Plugin exposes the configured jitter in seconds."""
    plugin = build_plugin(jitter_seconds=600)
    assert plugin.jitter_seconds == 600


def test_lifespan_on_app_init_attaches_lifespan() -> None:
    """Plugin.on_app_init() attaches lifespan context manager to app config.

    The Litestar app calls on_app_init() during startup, allowing plugins to
    register lifespan handlers. This test verifies the plugin correctly appends
    its lifespan context manager to the app's lifespan list.
    """
    plugin = build_plugin(name="test-lifespan")
    mock_config = MagicMock()
    mock_config.lifespan = []
    plugin.on_app_init(mock_config)
    assert mock_config.lifespan == [plugin.lifespan]


async def test_lifespan_creates_task_on_enter(mock_app: MagicMock) -> None:
    """Lifespan context manager creates background job task on entry."""
    plugin = build_plugin(name="test-create")
    async with plugin.lifespan(mock_app):
        assert len(tasks_named(plugin.name)) == 1


async def test_lifespan_cancels_task_on_exit(mock_app: MagicMock) -> None:
    """Lifespan context manager cancels background job task on exit."""
    plugin = build_plugin(name="test-cancel")
    task_ref = None
    async with plugin.lifespan(mock_app):
        task_ref = tasks_named(plugin.name)[0]
    assert task_ref.cancelled()


async def test_lifespan_task_name_matches_plugin_name(mock_app: MagicMock) -> None:
    """Background job task is named after plugin name parameter."""
    plugin = build_plugin(name="my-job")
    async with plugin.lifespan(mock_app):
        assert tasks_named(plugin.name)


async def test_job_execution_callback_is_invoked(mock_app: MagicMock) -> None:
    """Job callback is invoked when job loop executes.

    The callback is called repeatedly on interval. This test verifies the first
    execution is scheduled and executed within the lifespan context.
    """
    called = asyncio.Event()

    async def signal() -> int:
        called.set()
        return 42

    plugin = run_immediately(build_plugin(job_callback=signal))

    async with plugin.lifespan(mock_app):
        await asyncio.wait_for(called.wait(), timeout=2.0)


async def test_job_execution_loop_survives_repeated_failures(
    mock_app: MagicMock,
) -> None:
    """Job loop continues executing even when callback raises exceptions.

    This is critical for reliability: transient errors should not crash the job
    loop. The loop should catch exceptions, log them, and retry on the next interval.

    Branch coverage:
    - Call 1: raises RuntimeError (caught, job loop continues)
    - Call 2: raises RuntimeError (caught, job loop continues)
    - Call 3: succeeds (recovery verified via asyncio.Event)

    This demonstrates that a flaky job (like intermittent database issues) won't
    break the background job system.
    """
    recovered = asyncio.Event()
    call_count = {"n": 0}

    async def intermittent() -> int:
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise RuntimeError("transient")
        recovered.set()
        return 0

    plugin = run_immediately(build_plugin(job_callback=intermittent))

    async with plugin.lifespan(mock_app):
        await asyncio.wait_for(recovered.wait(), timeout=2.0)
    assert call_count["n"] >= 3


async def test_job_execution_timeout_error_is_caught(mock_app: MagicMock) -> None:
    """TimeoutError from callback is caught and does not crash the job loop.

    Unlike CancelledError or KeyboardInterrupt, TimeoutError is treated as a
    transient failure. The loop should catch it and retry on next interval.
    """
    called = asyncio.Event()
    call_count = {"n": 0}

    async def times_out() -> int:
        call_count["n"] += 1
        called.set()
        raise TimeoutError

    plugin = run_immediately(build_plugin(job_callback=times_out))

    async with plugin.lifespan(mock_app):
        await asyncio.wait_for(called.wait(), timeout=2.0)
    assert call_count["n"] >= 1


async def test_job_execution_cancelled_error_propagates() -> None:
    """CancelledError from task cancellation propagates up (not caught).

    When the task is cancelled externally, CancelledError should propagate to
    complete the task cancellation cleanly, not be caught by exception handlers.
    This is critical for graceful shutdown.
    """
    completed = asyncio.Event()

    async def signalling_job() -> int:
        completed.set()
        return 0

    plugin = run_immediately(build_plugin(job_callback=signalling_job))

    task = asyncio.create_task(plugin.run_forever())
    await asyncio.wait_for(completed.wait(), timeout=2.0)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    assert task.cancelled()


async def test_job_execution_cancelled_error_inside_callback_propagates() -> None:
    """CancelledError raised inside callback propagates (cancellation is clean).

    If task is cancelled while the callback is executing, CancelledError should
    propagate from the callback and up through the job loop to complete shutdown.
    This ensures callbacks can't silently swallow cancellation signals.
    """
    entered = asyncio.Event()

    async def blocking_job() -> int:
        entered.set()
        await asyncio.Event().wait()

    plugin = run_immediately(build_plugin(job_callback=blocking_job))

    task = asyncio.create_task(plugin.run_forever())
    await asyncio.wait_for(entered.wait(), timeout=2.0)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    assert task.cancelled()
