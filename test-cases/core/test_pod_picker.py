"""Unit tests for PodPicker's outbound-pool generalization.

Source: core/services/pod_picker.py — ``for_outbound`` picks from the dedicated outbound voice-pod
pool (prefix), and ``internal_base_for`` builds the intra-cluster headless-DNS hand-off URL.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import core.services.pod_picker as pp
from core.services.pod_picker import PodPicker


def test_default_prefix_is_inbound_call_worker(monkeypatch):
    monkeypatch.setattr(pp.settings, "CALL_WORKER_PREFIX", "staging-tone-call-worker")
    picker = PodPicker(MagicMock())
    assert picker.prefix == "staging-tone-call-worker"


def test_for_outbound_uses_outbound_prefix(monkeypatch):
    monkeypatch.setattr(pp.settings, "OUTBOUND_CALL_WORKER_PREFIX", "staging-tone-outbound-call-worker")
    picker = PodPicker.for_outbound(MagicMock())
    assert picker.prefix == "staging-tone-outbound-call-worker"


def test_internal_base_for_builds_headless_dns(monkeypatch):
    monkeypatch.setattr(pp.settings, "OUTBOUND_CALL_HEADLESS_SERVICE", "staging-tone-outbound-call-headless")
    monkeypatch.setattr(pp.settings, "POD_SYNC_NAMESPACE", "staging")
    monkeypatch.setattr(pp.settings, "OUTBOUND_CALL_WORKER_PORT", 8080)
    picker = PodPicker(MagicMock())
    pod = SimpleNamespace(name="staging-tone-outbound-call-worker-2", ordinal=2)
    assert picker.internal_base_for(pod) == (
        "http://staging-tone-outbound-call-worker-2.staging-tone-outbound-call-headless.staging.svc:8080"
    )


def test_internal_base_for_none_pod_is_none():
    assert PodPicker(MagicMock()).internal_base_for(None) is None
