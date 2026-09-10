"""Unit tests for the spoken-farewell detector.

Source: core/services/pipeline/farewell_detection.py::is_farewell. Ending-anchored
so a real closing triggers but a mid-sentence pleasantry does not.
"""

import pytest

from core.services.pipeline.farewell_detection import is_farewell


@pytest.mark.parametrize(
    "text",
    [
        # The exact farewells from the two prod incident logs.
        "Thank you for calling — have a great day!",
        "Alright, have a great day!",
        # Other clear closings.
        "Goodbye!",
        "Bye!",
        "Okay, take care.",
        "Have a nice day.",
        "Thanks for calling.",
        "Sure — thank you for calling, goodbye",
        "have a great day",  # bare, no punctuation
    ],
)
def test_detects_closing_farewell(text):
    assert is_farewell(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "How many guests will be staying with us?",
        "You're welcome! Just to summarize, you",
        "Could you please clarify the type of rooms you would like?",
        # farewell-ish words, but NOT at the end → must not trigger.
        "I hope you have a great day tomorrow, what else can I help with?",
        "Let me take care of that booking for you now.",
        "We offer single, double, and deluxe rooms.",
        "",
        "   ",
    ],
)
def test_ignores_non_closing(text):
    assert is_farewell(text) is False


def test_none_is_safe():
    assert is_farewell(None) is False
