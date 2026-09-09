"""Unit tests for the end_call confirmation guard.

Source: core/services/pipeline/tools/end_call_tool.py::_confirmation_valid.
Pure function over transcript entries + optional live user text — no async,
no mocks. Covers the standard two-step, express, unwired, and the transcript
race (live_user_text supplies the just-spoken confirmation the transcript
hasn't recorded yet).
"""

import pytest

from core.services.pipeline.tools.end_call_tool import _confirmation_valid


@pytest.mark.parametrize(
    "entries,live,expected",
    [
        # Unwired transcript → never deadlock.
        (None, None, True),
        # Empty / no user turn → block.
        ([], None, False),
        ([{"role": "assistant", "text": "Hi there"}], None, False),
        # Standard two-step flow (transcript only).
        (
            [
                {"role": "assistant", "text": "Can I end the call?"},
                {"role": "user", "text": "yes please"},
            ],
            None,
            True,
        ),
        # Express path (transcript only) — short direct user command.
        ([{"role": "user", "text": "hang up"}], None, True),
        # Long contextual mention of hanging up → NOT express, no ask → block.
        (
            [{"role": "user", "text": "I hope you don't hang up on me before we finish everything today"}],
            None,
            False,
        ),
        # RACE: transcript missing the trailing user turn; live text is the ask reply.
        ([{"role": "assistant", "text": "Can I end the call now?"}], "yes please", True),
        # RACE + express: live text itself is a direct end command.
        ([{"role": "assistant", "text": "Can I end the call now?"}], "you can end the call", True),
        # Live express path with an empty transcript.
        ([], "hang up", True),
        # Live text present, not a confirmation, and no preceding ask → block.
        ([{"role": "user", "text": "earlier turn"}], "tell me more about your pricing plans", False),
        # Blank live text → fall back to transcript standard path.
        (
            [
                {"role": "assistant", "text": "Can I end the call?"},
                {"role": "user", "text": "yes"},
            ],
            "   ",
            True,
        ),
        # Reported scenario: a direct end request on the FIRST turn (no prior
        # assistant ask) must be authorized via the express path, so the model
        # can end immediately instead of asking to confirm.
        ([{"role": "user", "text": "Can you end the call now?"}], None, True),
        ([], "Can you end the call now?", True),
        ([], "please end the call", True),
        ([], "please hang up", True),
        ([], "can you end the call", True),
        # Bare affirmatives replying to the agent's "Can I end the call?" ask
        # must be authorized (guard side of the #5 fix).
        ([{"role": "assistant", "text": "Can I end the call now?"}], "yeah", True),
        ([{"role": "assistant", "text": "Can I end the call now?"}], "sure", True),
        ([{"role": "assistant", "text": "Can I end the call now?"}], "okay", True),
        ([{"role": "assistant", "text": "Shall I go ahead and end the call?"}], "yep", True),
        # Regression (prod Telnyx log): the user reply is ALREADY in the
        # transcript AND live_user_text repeats it. The ask must still be found —
        # the old code appended a duplicate user turn and the lookback broke here,
        # wrongly blocking a valid "Yeah, please." confirmation.
        (
            [
                {"role": "assistant", "text": "Alright, thank you for calling. Can I end the call now?"},
                {"role": "user", "text": "Yeah, please."},
            ],
            "Yeah, please.",
            True,
        ),
        (
            [
                {"role": "user", "text": "book a room for two"},
                {"role": "assistant", "text": "Can I end the call now?"},
                {"role": "user", "text": "yes"},
            ],
            "yes",
            True,
        ),
    ],
)
def test_confirmation_valid(entries, live, expected):
    assert _confirmation_valid(entries, live_user_text=live) is expected
