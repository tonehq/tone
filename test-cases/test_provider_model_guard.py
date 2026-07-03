"""Unit tests for the provider/model_id consistency guards.

Covers the three layers added after the staging incident (2026-07-03) where a
stale ``stt_settings.model_id`` from a previous provider redirected Deepgram
STT to the parakeet k8s base_url:

  - save path: ``AgentService._reconcile_target_model_ids`` rewrites/drops/
    rejects a model_id that doesn't belong to ``settings.provider_id``;
  - resolver defense: ``_build_service_specs`` skips ``Model.base_url``
    injection when the model row's provider doesn't match the spec's;
  - audit: ``find_provider_model_mismatches`` reports corrupt rows.

Pure logic — no real DB. A small fake session evaluates SQLAlchemy filter
criteria against in-memory rows.

Run:
    pytest test-cases/test_provider_model_guard.py -v -o "addopts="
"""

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import core.services.pipeline.service_resolver as sr
from core.models.agent_config import AgentConfig
from core.models.model import Model
from core.models.model_provider import ModelProvider
from core.services.agent_service import AgentService
from core.services.config_audit import find_provider_model_mismatches
from core.services.pipeline.service_resolver import _build_service_specs


# ── fake SQLAlchemy session ──────────────────────────────────────────────────

def _crit_matches(row, crit):
    """Evaluate a simple SQLAlchemy binary criterion against a plain object."""
    col = crit.left.name
    actual = getattr(row, col, None)
    right = getattr(crit, "right", None)
    value = getattr(right, "value", None)
    op_name = getattr(crit.operator, "__name__", "")
    if op_name == "is_":
        # .is_(None)/.is_(True)/.is_(False) render as Null()/True_()/False_()
        # constructs, not bind params — map them back to python singletons.
        rtype = type(right).__name__
        singleton = {"Null": None, "True_": True, "False_": False}.get(rtype, value)
        return actual is singleton
    if op_name in ("in_op", "in_"):
        return actual in (value or ())
    return actual == value


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *crits):
        return FakeQuery([r for r in self.rows if all(_crit_matches(r, c) for c in crits)])

    def order_by(self, *args):
        return self

    def all(self):
        return list(self.rows)

    def first(self):
        return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self, rows_by_cls):
        self.rows_by_cls = rows_by_cls

    def query(self, cls):
        return FakeQuery(list(self.rows_by_cls.get(cls, [])))


# ── shared catalog fixtures ──────────────────────────────────────────────────

DEEPGRAM_PID = uuid.uuid4()
PARAKEET_PID = uuid.uuid4()

DG_MODEL = SimpleNamespace(
    id=uuid.uuid4(), provider_id=DEEPGRAM_PID, kind="stt",
    name="nova-2-conversationalai", base_url=None,
    meta_data_schema=None, updated_at=None, is_active=True, deleted_at=None,
)
PK_MODEL = SimpleNamespace(
    id=uuid.uuid4(), provider_id=PARAKEET_PID, kind="stt",
    name="parakeet-tdt-0.6b-v2",
    base_url="http://staging-stt-parakeet-service.staging.svc.cluster.local",
    meta_data_schema=None, updated_at=None, is_active=True, deleted_at=None,
)
LLM_PID = uuid.uuid4()
LLM_MODEL = SimpleNamespace(
    id=uuid.uuid4(), provider_id=LLM_PID, kind="llm", name="gpt-4o",
    base_url=None, meta_data_schema=None, updated_at=None,
    is_active=True, deleted_at=None,
)


def _svc(models):
    svc = AgentService.__new__(AgentService)
    svc.db = FakeDB({Model: models})
    return svc


def _config(**settings):
    base = {"llm_settings": None, "stt_settings": None, "voice_settings": None}
    base.update(settings)
    return SimpleNamespace(id=uuid.uuid4(), **base)


# ── save-path reconciliation ─────────────────────────────────────────────────

class TestReconcileTargetModelIds:
    def test_mismatched_stt_model_id_is_reresolved_by_name(self):
        """Deepgram provider + parakeet model_id + deepgram model name →
        model_id is rewritten to the deepgram model row."""
        target = _config(stt_settings={
            "provider_id": str(DEEPGRAM_PID),
            "model": "nova-2-conversationalai",
            "model_id": str(PK_MODEL.id),
        })
        _svc([DG_MODEL, PK_MODEL])._reconcile_target_model_ids(target)
        assert target.stt_settings["model_id"] == str(DG_MODEL.id)

    def test_missing_model_id_is_filled_from_name(self):
        """Provider switch cleared model_id; the name resolves it back."""
        target = _config(stt_settings={
            "provider_id": str(DEEPGRAM_PID),
            "model": "nova-2-conversationalai",
        })
        _svc([DG_MODEL, PK_MODEL])._reconcile_target_model_ids(target)
        assert target.stt_settings["model_id"] == str(DG_MODEL.id)

    def test_unresolvable_stale_id_is_dropped_when_name_present(self):
        """Cross-provider id + a name with no catalog row under the new
        provider → the stale id is dropped, the name literal stays."""
        target = _config(stt_settings={
            "provider_id": str(DEEPGRAM_PID),
            "model": "some-custom-model",
            "model_id": str(PK_MODEL.id),
        })
        _svc([DG_MODEL, PK_MODEL])._reconcile_target_model_ids(target)
        assert "model_id" not in target.stt_settings
        assert target.stt_settings["model"] == "some-custom-model"

    def test_cross_provider_id_without_name_is_rejected(self):
        """LLM settings carry no model name; a provably foreign model_id
        must fail validation instead of being persisted."""
        target = _config(llm_settings={
            "provider_id": str(LLM_PID),
            "model_id": str(PK_MODEL.id),
        })
        with pytest.raises(HTTPException) as exc:
            _svc([LLM_MODEL, PK_MODEL])._reconcile_target_model_ids(target)
        assert exc.value.status_code == 400
        assert "llm_settings" in exc.value.detail["errors"]

    def test_dangling_id_without_name_is_dropped(self):
        """model_id pointing at no catalog row (deleted model) with no name
        to re-resolve from — dropped with a warning, save proceeds."""
        target = _config(llm_settings={
            "provider_id": str(LLM_PID),
            "model_id": str(uuid.uuid4()),
        })
        _svc([LLM_MODEL])._reconcile_target_model_ids(target)
        assert "model_id" not in target.llm_settings

    def test_consistent_settings_are_untouched(self):
        settings = {
            "provider_id": str(DEEPGRAM_PID),
            "model": "nova-2-conversationalai",
            "model_id": str(DG_MODEL.id),
        }
        target = _config(stt_settings=settings)
        _svc([DG_MODEL, PK_MODEL])._reconcile_target_model_ids(target)
        assert target.stt_settings is settings  # same object — no rewrite

    def test_settings_without_provider_are_skipped(self):
        settings = {"model": "whatever", "model_id": str(PK_MODEL.id)}
        target = _config(stt_settings=settings)
        _svc([DG_MODEL, PK_MODEL])._reconcile_target_model_ids(target)
        assert target.stt_settings is settings

    def test_only_scopes_reconciliation_to_named_blocks(self):
        """A corrupt STT block is ignored when ``only`` doesn't include it."""
        stt = {"provider_id": str(DEEPGRAM_PID), "model_id": str(PK_MODEL.id)}
        target = _config(stt_settings=stt)
        _svc([DG_MODEL, PK_MODEL])._reconcile_target_model_ids(
            target, only={"llm_settings"}
        )
        assert target.stt_settings is stt  # untouched — not in `only`


class TestApplyConfigFieldsScoping:
    """Case C/D: a save that doesn't carry a settings block must never be
    blocked or silently mutated by a pre-existing corrupt block."""

    def _target(self, **kw):
        base = {
            "id": uuid.uuid4(), "agent_id": uuid.uuid4(),
            "llm_settings": None, "stt_settings": None, "voice_settings": None,
        }
        base.update(kw)
        return SimpleNamespace(**base)

    def test_first_message_only_edit_does_not_reject_corrupt_llm(self):
        # Pre-existing cross-provider LLM id with no `model` name to re-resolve
        # from — reconciling it would raise 400. The edit doesn't touch it, so
        # it must pass untouched.
        target = self._target(
            llm_settings={"provider_id": str(LLM_PID), "model_id": str(PK_MODEL.id)},
            first_message=None,
        )
        _svc([LLM_MODEL, PK_MODEL])._apply_config_fields(
            target, {"first_message": "Hello"}
        )
        assert target.first_message == "Hello"
        assert target.llm_settings["model_id"] == str(PK_MODEL.id)  # untouched

    def test_written_stt_block_is_reconciled(self):
        target = self._target()
        _svc([DG_MODEL, PK_MODEL])._apply_config_fields(
            target,
            {"stt_settings": {
                "provider_id": str(DEEPGRAM_PID),
                "model": "nova-2-conversationalai",
                "model_id": str(PK_MODEL.id),
            }},
        )
        assert target.stt_settings["model_id"] == str(DG_MODEL.id)  # rewritten


# ── resolver defense ─────────────────────────────────────────────────────────

ORG_ID = uuid.uuid4()


def _resolver_db(models):
    dg_provider = SimpleNamespace(id=DEEPGRAM_PID, slug="deepgram")
    pk_provider = SimpleNamespace(id=PARAKEET_PID, slug="parakeet")
    dg_key = SimpleNamespace(
        id=1, provider_id=DEEPGRAM_PID, organization_id=ORG_ID,
        service_type="stt", encrypted_key="enc", is_active=True, is_default=True,
    )
    pk_key = SimpleNamespace(
        id=2, provider_id=PARAKEET_PID, organization_id=ORG_ID,
        service_type="stt", encrypted_key="enc", is_active=True, is_default=True,
    )
    llm_key = SimpleNamespace(
        id=3, provider_id=LLM_PID, organization_id=ORG_ID,
        service_type="llm", encrypted_key="enc", is_active=True, is_default=True,
    )
    llm_provider = SimpleNamespace(id=LLM_PID, slug="openai")
    return FakeDB({
        sr.ModelProvider: [dg_provider, pk_provider, llm_provider],
        sr.Model: models,
        sr.ApiKey: [dg_key, pk_key, llm_key],
        sr.ModelVoice: [],
    })


def _resolver_config(stt_settings):
    return SimpleNamespace(
        agent_id=uuid.uuid4(),
        llm_settings={"provider_id": str(LLM_PID), "model_id": str(LLM_MODEL.id)},
        stt_settings=stt_settings,
        voice_settings={},
        system_prompt_template="You are a test agent.",
        mode="prompt",
        workflow_id=None,
    )


class TestResolverBaseUrlDefense:
    @pytest.fixture(autouse=True)
    def _stub_decrypt(self, monkeypatch):
        monkeypatch.setattr(sr, "decrypt", lambda v: "sk-test")

    def test_mismatched_model_id_does_not_inject_base_url(self):
        """Corrupt config (deepgram provider + parakeet model_id): the
        parakeet base_url must NOT leak into the deepgram STT spec."""
        config = _resolver_config({
            "provider_id": str(DEEPGRAM_PID),
            "model": "nova-2-conversationalai",
            "model_id": str(PK_MODEL.id),
        })
        db = _resolver_db([DG_MODEL, PK_MODEL, LLM_MODEL])
        _llm, stt, _tts, _s2s = _build_service_specs(db, ORG_ID, config)
        assert stt is not None
        assert stt["provider_name"] == "deepgram"
        assert "base_url" not in stt["metadata"]
        # The model name literal still drives the call.
        assert stt["model_name"] == "nova-2-conversationalai"

    def test_matching_model_id_injects_base_url(self):
        config = _resolver_config({
            "provider_id": str(PARAKEET_PID),
            "model": PK_MODEL.name,
            "model_id": str(PK_MODEL.id),
        })
        db = _resolver_db([DG_MODEL, PK_MODEL, LLM_MODEL])
        _llm, stt, _tts, _s2s = _build_service_specs(db, ORG_ID, config)
        assert stt is not None
        assert stt["metadata"]["base_url"] == PK_MODEL.base_url


# ── audit ────────────────────────────────────────────────────────────────────

class TestMismatchAudit:
    def _audit_db(self, configs):
        return FakeDB({
            AgentConfig: configs,
            Model: [DG_MODEL, PK_MODEL, LLM_MODEL],
            ModelProvider: [
                SimpleNamespace(id=DEEPGRAM_PID, slug="deepgram"),
                SimpleNamespace(id=PARAKEET_PID, slug="parakeet"),
                SimpleNamespace(id=LLM_PID, slug="openai"),
            ],
        })

    def _cfg(self, stt_settings, deleted_at=None):
        return SimpleNamespace(
            id=uuid.uuid4(), agent_id=uuid.uuid4(), version=1,
            deleted_at=deleted_at,
            llm_settings=None, stt_settings=stt_settings, voice_settings=None,
        )

    def test_reports_provider_mismatch(self):
        corrupt = self._cfg({
            "provider_id": str(DEEPGRAM_PID),
            "model": "nova-2-conversationalai",
            "model_id": str(PK_MODEL.id),
        })
        clean = self._cfg({
            "provider_id": str(DEEPGRAM_PID),
            "model_id": str(DG_MODEL.id),
        })
        rows = find_provider_model_mismatches(self._audit_db([corrupt, clean]))
        assert len(rows) == 1
        assert rows[0]["agent_config_id"] == str(corrupt.id)
        assert rows[0]["settings_key"] == "stt_settings"
        assert rows[0]["reason"] == "provider_mismatch"
        assert rows[0]["provider_slug"] == "deepgram"
        assert rows[0]["model_provider_slug"] == "parakeet"

    def test_reports_dangling_model_id(self):
        dangling = self._cfg({
            "provider_id": str(DEEPGRAM_PID),
            "model_id": str(uuid.uuid4()),
        })
        rows = find_provider_model_mismatches(self._audit_db([dangling]))
        assert len(rows) == 1
        assert rows[0]["reason"] == "model_not_found"

    def test_soft_deleted_configs_are_skipped(self):
        corrupt = self._cfg(
            {"provider_id": str(DEEPGRAM_PID), "model_id": str(PK_MODEL.id)},
            deleted_at="2026-07-03",
        )
        assert find_provider_model_mismatches(self._audit_db([corrupt])) == []

    def test_clean_db_returns_zero_rows(self):
        clean = self._cfg({
            "provider_id": str(PARAKEET_PID),
            "model_id": str(PK_MODEL.id),
        })
        assert find_provider_model_mismatches(self._audit_db([clean])) == []
