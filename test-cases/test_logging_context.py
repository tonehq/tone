"""Unit tests for the trace_id / job_id log-context contract (core/logging.py).

Proves the two guarantees the observability model depends on:
  * ``trace_id`` and ``job_id`` are two INDEPENDENT log keys — a line can carry
    either, both, or neither, and setting one never touches the other.
  * Each id is strictly LIFECYCLE-BOUNDED: ``job_logging_context`` binds job_id
    for its block only, and ``isolated_trace_context`` starts trace-clean and
    restores the prior trace on exit — so a trace configured inside one job can
    never leak into the next job on a reused worker thread.

Pure logic — no DB, no network. Run:
    pytest test-cases/test_logging_context.py -v -o "addopts="
"""

import pytest
from loguru import logger

import core.logging as L


@pytest.fixture(autouse=True)
def _reset_log_context():
    """Reset the trace/job contextvars AND the sink after each test.

    The contextvars are module-level and persist across tests in one process, so
    without this a trace_id one test sets would bleed into the next test's
    assertions. (This is the test-suite mirror of the cross-job leak the
    isolated_trace_context production code prevents.)"""
    yield
    for var, default in L._TRACE_VARS:
        var.set(default)
    L.set_job_id(None)
    L.setup_logging("INFO")


@pytest.fixture
def captured():
    """Capture rendered log lines (with the real _LOG_FORMAT) into a list."""
    L.setup_logging("INFO")
    lines: list[str] = []
    sink_id = logger.add(lines.append, format=L._LOG_FORMAT, level="INFO")
    try:
        yield lines
    finally:
        logger.remove(sink_id)


# --- independence: two separate keys ---------------------------------------

def test_trace_and_job_are_independent_keys(captured):
    logger.info("neither")
    L.set_trace_id("call-xyz")
    logger.info("trace only")
    with L.job_logging_context(999):
        logger.info("both")
    logger.info("trace remains after job")

    joined = "\n".join(captured)
    # every rendered line carries BOTH keys as distinct fields
    for line in captured:
        assert "trace_id=" in line and "job_id=" in line

    assert "trace_id=none | job_id=none | neither" in joined
    assert "trace_id=call-xyz | job_id=none | trace only" in joined
    assert "trace_id=call-xyz | job_id=999 | both" in joined
    # job_id fell back to none but the independent trace_id is untouched
    assert "trace_id=call-xyz | job_id=none | trace remains after job" in joined


# --- job_id is bounded to its block only -----------------------------------

def test_job_id_bounded_to_block():
    assert L.get_job_id() == "none"
    with L.job_logging_context(42):
        assert L.get_job_id() == "42"
    assert L.get_job_id() == "none"  # restored on exit


def test_job_id_none_when_id_missing():
    with L.job_logging_context(None):
        assert L.get_job_id() == "none"


# --- trace is bounded per job: no leak across sequential jobs ---------------

def _run_job(job_id, body):
    """Mimic ingestion_queue._with_job_logging on a reused worker context."""
    with L.isolated_trace_context(), L.job_logging_context(job_id):
        body()


def test_trace_does_not_leak_between_jobs(captured):
    # Job A configures its own (ingestion) trace mid-run.
    def job_a():
        logger.info("A-before-trace")
        L.start_ingestion_trace("run7")
        logger.info("A-after-trace")

    # Job B (same context) configures NO trace — must log trace_id=none.
    def job_b():
        logger.info("B-no-trace")

    _run_job(101, job_a)
    _run_job(202, job_b)

    joined = "\n".join(captured)
    assert "trace_id=none | job_id=101 | A-before-trace" in joined
    assert "-ing-run7 | job_id=101 | A-after-trace" in joined
    # THE KEY ASSERTION: job A's trace did not leak into job B.
    assert "trace_id=none | job_id=202 | B-no-trace" in joined

    # After both jobs, context is fully restored.
    assert L.get_trace_id() == "none"
    assert L.get_job_id() == "none"


def test_isolated_trace_context_restores_prior_trace():
    L.set_trace_id("outer-trace")
    with L.isolated_trace_context():
        assert L.get_trace_id() == "none"       # starts clean
        L.set_trace_id("inner-trace")
        assert L.get_trace_id() == "inner-trace"
    assert L.get_trace_id() == "outer-trace"     # prior value restored
