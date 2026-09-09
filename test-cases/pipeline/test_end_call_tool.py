"""Unit tests for the end_call tool handler.

Source: core/services/pipeline/tools/end_call_tool.py::create_end_call_handler.
The regex confirmation gate was removed (it false-blocked valid ends — e.g. when
STT mis-heard "end" as "send"); the handler now trusts the LLM's decision and
only guards against a double-call (single-fire). Driven with asyncio.run over
duck-typed params, mirroring test_tool_call_timing.py.
"""

import asyncio
from types import SimpleNamespace

from pipecat.frames.frames import EndFrame

from core.services.pipeline.tools.end_call_tool import create_end_call_handler


def _make_params(reason="user said 'end the call'"):
    queued = []
    results = []

    async def _queue_frame(frame):
        queued.append(frame)

    async def _result_callback(result, **kwargs):
        results.append(result)

    params = SimpleNamespace(
        tool_call_id="tc-1",
        function_name="end_call",
        arguments={"reason": reason},
        pipeline_worker=SimpleNamespace(queue_frame=_queue_frame),
        result_callback=_result_callback,
        context=None,
        llm=None,
    )
    return params, queued, results


def test_end_call_queues_endframe_and_stamps_reason():
    end_reason_holder = {"reason": None, "detail": None}
    handler = create_end_call_handler(
        end_reason_holder=end_reason_holder, current_turn={"number": 2}
    )
    params, queued, results = _make_params()

    asyncio.run(handler(params))

    assert any(isinstance(f, EndFrame) for f in queued), "should queue an EndFrame"
    assert end_reason_holder["reason"] == "llm_end_call"
    assert end_reason_holder["detail"] == "user said 'end the call'"
    assert results == ["Call ending now."]


def test_end_call_does_not_block_on_odd_phrasing():
    # No confirmation re-check: even a phrasing the old regex would reject (e.g.
    # STT's "send the call") ends the call — the LLM already decided.
    end_reason_holder = {"reason": None, "detail": None}
    handler = create_end_call_handler(end_reason_holder=end_reason_holder)
    params, queued, results = _make_params(reason="user said 'send the call now'")

    asyncio.run(handler(params))

    assert any(isinstance(f, EndFrame) for f in queued)
    assert results == ["Call ending now."]


def test_end_call_single_fire_ignores_second_call():
    handler = create_end_call_handler(end_reason_holder={"reason": None, "detail": None})
    params, queued, results = _make_params()

    asyncio.run(handler(params))
    asyncio.run(handler(params))

    assert sum(isinstance(f, EndFrame) for f in queued) == 1, "at most one EndFrame"
    assert results[-1] == "Call is already ending."
