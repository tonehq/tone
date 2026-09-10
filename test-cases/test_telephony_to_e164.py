import pytest

from core.utils.telephony import to_e164


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("13474282218", "+13474282218"),
        ("+13474282218", "+13474282218"),
        (" +1 555 000 1111 ", "+15550001111"),
        ("sip:agent@example.com", "sip:agent@example.com"),
        ("anonymous", "anonymous"),
        ("", ""),
        (None, None),
    ],
)
def test_to_e164(raw, expected):
    assert to_e164(raw) == expected
