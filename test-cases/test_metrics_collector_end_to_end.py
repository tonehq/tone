"""Unit tests for MetricsCollectorProcessor.end_to_end latency.

Pure logic — no DB, no async frame plumbing. Exercises the private hooks
directly with a patched ``time.time()`` so we can assert the exact
end_to_end wall-clock math under VAD-flap and clean-stop conditions.

Run:
    pytest test-cases/test_metrics_collector_end_to_end.py -v -o "addopts="
"""

from unittest.mock import patch

import pytest

from core.processors import metrics_collector as mc
from core.processors.metrics_collector import MetricsCollectorProcessor


@pytest.fixture
def processor():
    return MetricsCollectorProcessor()


def _feed(processor, sequence):
    """Drive the processor through a scripted sequence of (time, action) pairs.

    action is one of: 'turn_start', 'turn_end', 'user_stopped',
    'user_started', 'bot_started'.
    """
    for now, action in sequence:
        with patch.object(mc.time, "time", return_value=now):
            if action == "turn_start":
                processor.on_turn_started(1)
            elif action == "turn_end":
                processor.on_turn_ended(1)
            elif action == "user_stopped":
                processor._mark_user_stopped()
            elif action == "user_started":
                processor._mark_user_started()
            elif action == "bot_started":
                processor._mark_bot_started()
            else:
                raise ValueError(f"unknown action: {action}")


class TestEndToEndLatency:
    """turn_metrics[].end_to_end = bot_started_at - user_stopped_at

    Must use the *latest* user-stop before bot-start (matches user-perceived
    latency), not the first stop of the turn. This mirrors
    UserBotLatencyObserver semantics so both metrics agree.
    """

    def test_vad_flap_uses_latest_user_stop(self, processor):
        """User pauses mid-sentence, resumes, then really stops.

        Regression: prior behavior locked the first stop (t=10.0) and
        reported end_to_end=2.5, wrongly counting user-talking time as
        bot latency. Now uses the last stop before bot-start (t=11.0)
        for a correct 1.5.
        """
        _feed(processor, [
            (9.0,  "turn_start"),
            (10.0, "user_stopped"),   # false stop mid-sentence
            (10.3, "user_started"),   # user resumed talking
            (11.0, "user_stopped"),   # real stop
            (12.5, "bot_started"),
            (13.0, "turn_end"),
        ])
        turn = processor.get_turn_metrics()[0]
        assert turn["end_to_end"] == 1.5
        assert turn["user_stopped_at"] == 11.0
        assert turn["bot_started_at"] == 12.5

    def test_clean_single_stop_unchanged(self, processor):
        """No VAD flap: latest-stop == first-stop, value must be unchanged."""
        _feed(processor, [
            (9.0,  "turn_start"),
            (10.0, "user_stopped"),
            (10.8, "bot_started"),
            (11.0, "turn_end"),
        ])
        turn = processor.get_turn_metrics()[0]
        assert turn["end_to_end"] == 0.8

    def test_multiple_flaps_still_uses_last_stop(self, processor):
        """Several stop/start cycles — only the final stop should count."""
        _feed(processor, [
            (9.0,  "turn_start"),
            (10.0, "user_stopped"),
            (10.2, "user_started"),
            (10.5, "user_stopped"),
            (10.7, "user_started"),
            (11.0, "user_stopped"),   # final real stop
            (12.0, "bot_started"),
            (12.5, "turn_end"),
        ])
        turn = processor.get_turn_metrics()[0]
        assert turn["end_to_end"] == 1.0

    def test_only_first_bot_start_counts(self, processor):
        """Bot-start is still first-wins within the turn (tool-call restart etc.)."""
        _feed(processor, [
            (9.0,  "turn_start"),
            (10.0, "user_stopped"),
            (11.0, "bot_started"),    # first — this is the user-felt edge
            (11.5, "bot_started"),    # tool-call resume; must be ignored
            (12.0, "turn_end"),
        ])
        turn = processor.get_turn_metrics()[0]
        assert turn["bot_started_at"] == 11.0
        assert turn["end_to_end"] == 1.0

    def test_user_started_before_any_stop_is_noop(self, processor):
        """A stray user-started with no prior stop must not blow up."""
        _feed(processor, [
            (9.0,  "turn_start"),
            (9.5,  "user_started"),   # no prior stop to reset — no-op
            (10.0, "user_stopped"),
            (10.5, "bot_started"),
            (11.0, "turn_end"),
        ])
        turn = processor.get_turn_metrics()[0]
        assert turn["end_to_end"] == 0.5

    def test_end_to_end_null_when_bot_never_starts(self, processor):
        """No bot-start => end_to_end stays null (unchanged behavior)."""
        _feed(processor, [
            (9.0,  "turn_start"),
            (10.0, "user_stopped"),
            (11.0, "turn_end"),
        ])
        turn = processor.get_turn_metrics()[0]
        assert turn["end_to_end"] is None

    def test_interruption_stop_does_not_overwrite_anchor(self, processor):
        """User interrupts the bot mid-reply — the interruption's stop must
        NOT become this turn's user_stopped_at.

        Regression for the negative-end_to_end bug: on interrupted turns the
        caller barges in after the bot has started speaking (user_started →
        user_stopped). That trailing stop landed in the same turn buffer and
        overwrote user_stopped_at to a time AFTER bot_started_at, so
        end_to_end came out negative (e.g. -0.7s). The anchor must freeze at
        the real pre-response stop once the bot has started.
        """
        _feed(processor, [
            (9.0,  "turn_start"),
            (10.0, "user_stopped"),   # real question ends here
            (10.6, "bot_started"),    # bot replies -> anchor must freeze
            (11.2, "user_started"),   # caller interrupts the bot
            (11.8, "user_stopped"),   # interruption stop — must be ignored here
            (12.0, "turn_end"),
        ])
        turn = processor.get_turn_metrics()[0]
        assert turn["user_stopped_at"] == 10.0
        assert turn["bot_started_at"] == 10.6
        assert turn["end_to_end"] == 0.6  # positive, not -1.2

    def test_flap_before_bot_still_overwrites_then_freezes(self, processor):
        """Pre-bot flaps still take the latest stop; post-bot stops are frozen.

        Guards that the freeze does not regress the VAD-flap handling: the
        latest stop *before* bot-start still wins, and only stops *after*
        bot-start are ignored.
        """
        _feed(processor, [
            (9.0,  "turn_start"),
            (10.0, "user_stopped"),   # false stop mid-sentence
            (10.3, "user_started"),   # resumed
            (11.0, "user_stopped"),   # real stop before bot -> should win
            (12.5, "bot_started"),    # anchor freezes at 11.0
            (13.0, "user_started"),   # interruption
            (13.4, "user_stopped"),   # ignored
            (14.0, "turn_end"),
        ])
        turn = processor.get_turn_metrics()[0]
        assert turn["user_stopped_at"] == 11.0
        assert turn["end_to_end"] == 1.5
