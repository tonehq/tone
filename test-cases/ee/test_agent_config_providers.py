"""Tests for Agent Config provider-specific metadata (EE edition).

Tests upsert_agent_config with ALL provider-specific metadata schemas.
Integration tests — real DB, real endpoints, no mocks.
Each provider's metadata fields are tested with realistic values from dev-data.json.

Postman collection reference: postman_collection/agent_configs.postman_collection.json
"""

import pytest
import uuid


# ─── Helpers ───


def _create_agent(client, name=None):
    """Create an agent via API and return its ID."""
    name = name or f"provider-test-{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/v1/agent/upsert_agent", json={"name": name})
    assert resp.status_code == 200
    return resp.json()["id"]


def _resolve_provider(db_session, provider_name, service_type):
    """Look up service ID and first model ID. Returns (service_id, model_id) or (None, None).

    agent_config.*_service_id FKs to accounts(id).
    We find the model_provider_menu first, then look up the corresponding account record.
    """
    from core.models.model_provider_menu import ModelProviderMenu
    from core.models.account import Account
    from core.models.model_menu import ModelMenu

    provider = db_session.query(ModelProviderMenu).filter(
        ModelProviderMenu.name == provider_name,
        ModelProviderMenu.provider_type == service_type,
    ).first()
    if not provider:
        return None, None
    service = db_session.query(Account).filter(
        Account.model_provider_menu_id == provider.id,
        Account.service_type == service_type,
    ).first()
    if not service:
        return None, None
    model = db_session.query(ModelMenu).filter(
        ModelMenu.model_provider_menu_id == provider.id,
        ModelMenu.status == "active",
    ).first()
    model_id = model.id if model else None
    return service.id, model_id


def _upsert_config(client, agent_id, system_prompt="Test prompt.", **kwargs):
    """Post upsert_agent_config and return the response.

    Filters out None values from kwargs to avoid overwriting existing DB fields
    with NULL during upsert (ON CONFLICT UPDATE uses stmt.excluded which defaults
    to NULL for missing fields).
    """
    filtered = {k: v for k, v in kwargs.items() if v is not None}
    payload = {"agent_id": agent_id, "system_prompt": system_prompt, **filtered}
    return client.post("/api/v1/agent_config/upsert_agent_config", json=payload)


def _assert_metadata_keys(response_metadata, expected_metadata, exclude_keys=None):
    """Verify the response metadata contains all keys we sent (except excluded ones)."""
    exclude_keys = exclude_keys or set()
    for key, value in expected_metadata.items():
        if key in exclude_keys:
            continue
        assert key in response_metadata, f"Key '{key}' missing from response metadata"


# ─── LLM Provider Configs ───


class TestLLMProviderConfigs:
    """Test upsert_agent_config with LLM provider-specific metadata for each provider."""

    def test_openai_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "openai", "llm")
        if not provider_id:
            pytest.skip("openai provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7
        assert data["llm_metadata"]["frequency_penalty"] == 0.5

    def test_anthropic_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "anthropic", "llm")
        if not provider_id:
            pytest.skip("anthropic provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "enable_prompt_caching": True,
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_k": 40,
            "top_p": 0.9,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7
        assert data["llm_metadata"]["enable_prompt_caching"] is True

    def test_google_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "google", "llm")
        if not provider_id:
            pytest.skip("google provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_k": 40,
            "top_p": 0.9,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7
        assert data["llm_metadata"]["top_k"] == 40

    def test_groq_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "groq", "llm")
        if not provider_id:
            pytest.skip("groq provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7
        assert data["llm_metadata"]["seed"] == 42

    def test_openrouter_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "openrouter", "llm")
        if not provider_id:
            pytest.skip("openrouter provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7
        assert data["llm_metadata"]["max_tokens"] == 1024

    def test_cerebras_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "cerebras", "llm")
        if not provider_id:
            pytest.skip("cerebras provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7

    def test_deepseek_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "deepseek", "llm")
        if not provider_id:
            pytest.skip("deepseek provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7

    def test_qwen_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "qwen", "llm")
        if not provider_id:
            pytest.skip("qwen provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7

    def test_sambanova_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "sambanova", "llm")
        if not provider_id:
            pytest.skip("sambanova provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7

    def test_ollama_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "ollama", "llm")
        if not provider_id:
            pytest.skip("ollama provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7

    def test_grok_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "grok", "llm")
        if not provider_id:
            pytest.skip("grok provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7

    def test_perplexity_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "perplexity", "llm")
        if not provider_id:
            pytest.skip("perplexity provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7

    def test_azure_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "azure", "llm")
        if not provider_id:
            pytest.skip("azure provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7

    def test_nvidia_nim_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "nvidia_nim", "llm")
        if not provider_id:
            pytest.skip("nvidia_nim provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7

    def test_fireworks_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "fireworks", "llm")
        if not provider_id:
            pytest.skip("fireworks provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7

    def test_together_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "together", "llm")
        if not provider_id:
            pytest.skip("together provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7

    def test_aws_bedrock_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "aws_bedrock", "llm")
        if not provider_id:
            pytest.skip("aws_bedrock provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "aws_access_key": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLE",
            "aws_session_token": "",
            "aws_region": "us-east-1",
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7
        assert data["llm_metadata"]["aws_region"] == "us-east-1"

    def test_mistral_llm(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "mistral", "llm")
        if not provider_id:
            pytest.skip("mistral provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "seed": 42,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "max_completion_tokens": 2048,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["temperature"] == 0.7


# ─── STT Provider Configs ───


class TestSTTProviderConfigs:
    """Test upsert_agent_config with STT provider-specific metadata for each provider."""

    def test_deepgram_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "deepgram", "stt")
        if not provider_id:
            pytest.skip("deepgram STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
            "sample_rate": 16000,
            "language": "en",
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stt_metadata"]["language"] == "en"
        assert data["stt_metadata"]["sample_rate"] == 16000

    def test_openai_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "openai", "stt")
        if not provider_id:
            pytest.skip("openai STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
            "language": "en",
            "prompt": "Transcribe customer support calls",
            "temperature": 0.0,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stt_metadata"]["language"] == "en"
        assert data["stt_metadata"]["temperature"] == 0.0

    def test_groq_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "groq", "stt")
        if not provider_id:
            pytest.skip("groq STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
            "language": "en",
            "prompt": "Transcribe voice calls",
            "temperature": 0.0,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stt_metadata"]["language"] == "en"

    def test_sarvam_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "sarvam", "stt")
        if not provider_id:
            pytest.skip("sarvam STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
            "sample_rate": 16000,
            "language": "hi-IN",
            "prompt": "Transcribe Hindi calls",
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stt_metadata"]["language"] == "hi-IN"

    def test_assemblyai_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "assemblyai", "stt")
        if not provider_id:
            pytest.skip("assemblyai STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
            "language": "en",
            "sample_rate": 16000,
            "word_finalization_max_wait_time": 300,
            "end_of_turn_confidence_threshold": 0.5,
            "speech_model": "universal-streaming-english",
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stt_metadata"]["language"] == "en"
        assert data["stt_metadata"]["speech_model"] == "universal-streaming-english"

    def test_cartesia_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "cartesia", "stt")
        if not provider_id:
            pytest.skip("cartesia STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
            "sample_rate": 16000,
            "language": "en",
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stt_metadata"]["language"] == "en"

    def test_soniox_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "soniox", "stt")
        if not provider_id:
            pytest.skip("soniox STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
            "sample_rate": 16000,
            "language_hints": ["en"],
            "enable_speaker_diarization": False,
            "enable_language_identification": False,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stt_metadata"]["language_hints"] == ["en"]

    def test_elevenlabs_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "elevenlabs", "stt")
        if not provider_id:
            pytest.skip("elevenlabs STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
            "sample_rate": 16000,
            "language": "en",
            "tag_audio_events": True,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stt_metadata"]["language"] == "en"
        assert data["stt_metadata"]["tag_audio_events"] is True

    def test_gladia_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "gladia", "stt")
        if not provider_id:
            pytest.skip("gladia STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
            "region": "us-west",
            "sample_rate": 16000,
            "language": "en",
            "endpointing": 0.5,
            "enable_vad": False,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stt_metadata"]["language"] == "en"
        assert data["stt_metadata"]["region"] == "us-west"

    def test_hathora_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "hathora", "stt")
        if not provider_id:
            pytest.skip("hathora STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200

    def test_sambanova_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "sambanova", "stt")
        if not provider_id:
            pytest.skip("sambanova STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200

    def test_nvidia_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "nvidia", "stt")
        if not provider_id:
            pytest.skip("nvidia STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
            "server": "grpc.nvcf.nvidia.com:443",
            "sample_rate": 16000,
            "language": "en-US",
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stt_metadata"]["language"] == "en-US"
        assert data["stt_metadata"]["server"] == "grpc.nvcf.nvidia.com:443"

    def test_speechmatics_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "speechmatics", "stt")
        if not provider_id:
            pytest.skip("speechmatics STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
            "sample_rate": 16000,
            "domain": "general",
            "language": "en",
            "enable_diarization": False,
            "max_speakers": 2,
            "max_delay": 1.0,
            "end_of_utterance_silence_trigger": 0.5,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stt_metadata"]["language"] == "en"
        assert data["stt_metadata"]["domain"] == "general"

    def test_google_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "google", "stt")
        if not provider_id:
            pytest.skip("google STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
            "credentials": "",
            "credentials_path": "",
            "location": "global",
            "sample_rate": 16000,
            "languages": "en-US",
            "enable_automatic_punctuation": True,
            "enable_spoken_punctuation": False,
            "profanity_filter": False,
            "enable_word_time_offsets": False,
            "enable_word_confidence": False,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stt_metadata"]["languages"] == "en-US"
        assert data["stt_metadata"]["enable_automatic_punctuation"] is True

    def test_azure_stt(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "azure", "stt")
        if not provider_id:
            pytest.skip("azure STT provider not found in DB")
        agent_id = _create_agent(client_as_member)
        stt_metadata = {
            "model_id": model_id,
            "region": "eastus",
            "language": "en-US",
            "sample_rate": 16000,
            "endpoint_id": "",
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            stt_service_id=provider_id,
            stt_metadata=stt_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stt_metadata"]["language"] == "en-US"
        assert data["stt_metadata"]["region"] == "eastus"


# ─── TTS Provider Configs ───


class TestTTSProviderConfigs:
    """Test upsert_agent_config with TTS provider-specific metadata for each provider."""

    def test_cartesia_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "cartesia", "tts")
        if not provider_id:
            pytest.skip("cartesia TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "e07c00bc-4134-4eae-9ea4-1a55fb45746b",
            "language": "en",
            "speed": "normal",
            "emotion": ["positivity"],
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "e07c00bc-4134-4eae-9ea4-1a55fb45746b"
        assert data["tts_metadata"]["language"] == "en"

    def test_openai_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "openai", "tts")
        if not provider_id:
            pytest.skip("openai TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "alloy",
            "instructions": "Speak in a warm, friendly tone",
            "speed": 1.0,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "alloy"
        assert data["tts_metadata"]["speed"] == 1.0

    def test_elevenlabs_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "elevenlabs", "tts")
        if not provider_id:
            pytest.skip("elevenlabs TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "CwhRBWXzGAHq8TQ4Fs17",
            "language": "en",
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.5,
            "use_speaker_boost": True,
            "speed": 1.0,
            "auto_mode": True,
            "enable_ssml_parsing": False,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "CwhRBWXzGAHq8TQ4Fs17"
        assert data["tts_metadata"]["stability"] == 0.5

    def test_playht_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "playht", "tts")
        if not provider_id:
            pytest.skip("playht TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "s3://voice-cloning-zero-shot/example",
            "user_id": "your_playht_user_id",
            "language": "en",
            "speed": 1.0,
            "seed": 42,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "s3://voice-cloning-zero-shot/example"

    def test_deepgram_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "deepgram", "tts")
        if not provider_id:
            pytest.skip("deepgram TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "aura-2-helena-en",
            "sample_rate": 24000,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "aura-2-helena-en"

    def test_groq_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "groq", "tts")
        if not provider_id:
            pytest.skip("groq TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "orpheus-en-charon",
            "language": "en",
            "speed": 1.0,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "orpheus-en-charon"

    def test_hathora_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "hathora", "tts")
        if not provider_id:
            pytest.skip("hathora TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "af_heart",
            "speed": 1.0,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "af_heart"

    def test_minimax_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "minimax", "tts")
        if not provider_id:
            pytest.skip("minimax TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "female-qn-qingse",
            "group_id": "your_minimax_group_id",
            "language": "en",
            "speed": 1.0,
            "volume": 1.0,
            "pitch": 0,
            "emotion": "happy",
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "female-qn-qingse"
        assert data["tts_metadata"]["emotion"] == "happy"

    def test_rime_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "rime", "tts")
        if not provider_id:
            pytest.skip("rime TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "albion",
            "language": "english",
            "speed_alpha": 1.0,
            "reduce_latency": False,
            "pause_between_brackets": False,
            "phonemize_between_brackets": False,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "albion"

    def test_sarvam_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "sarvam", "tts")
        if not provider_id:
            pytest.skip("sarvam TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "sarvam-shubh-hi-IN",
            "language": "hi-IN",
            "pitch": 0.0,
            "pace": 1.0,
            "loudness": 1.0,
            "enable_preprocessing": False,
            "temperature": 0.6,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "sarvam-shubh-hi-IN"
        assert data["tts_metadata"]["language"] == "hi-IN"

    def test_fish_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "fish", "tts")
        if not provider_id:
            pytest.skip("fish TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "0eb2bd3576714dbcad7cd4c6b2b6e12f",
            "language": "en",
            "latency": "normal",
            "normalize": True,
            "prosody_speed": 1.0,
            "prosody_volume": 0,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "0eb2bd3576714dbcad7cd4c6b2b6e12f"

    def test_inworld_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "inworld", "tts")
        if not provider_id:
            pytest.skip("inworld TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "inworld_voice_1",
            "temperature": 0.5,
            "speaking_rate": 1.0,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "inworld_voice_1"

    def test_resemble_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "resemble", "tts")
        if not provider_id:
            pytest.skip("resemble TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "resemble_voice_uuid",
            "sample_rate": 22050,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "resemble_voice_uuid"

    def test_nvidia_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "nvidia", "tts")
        if not provider_id:
            pytest.skip("nvidia TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "English-US.Female-1",
            "server": "grpc.nvcf.nvidia.com:443",
            "language": "en-US",
            "quality": 20,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "English-US.Female-1"

    def test_neuphonic_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "neuphonic", "tts")
        if not provider_id:
            pytest.skip("neuphonic TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "6654e5a9-143e-46f4-a44a-4fcb9e1fe2a6",
            "language": "en",
            "speed": 1.0,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "6654e5a9-143e-46f4-a44a-4fcb9e1fe2a6"

    def test_lmnt_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "lmnt", "tts")
        if not provider_id:
            pytest.skip("lmnt TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "ava",
            "language": "en",
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "ava"

    def test_hume_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "hume", "tts")
        if not provider_id:
            pytest.skip("hume TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "d8ab67c6-953d-4bd8-9370-8fa53a0f1453",
            "description": "Warm and empathetic customer support agent",
            "speed": 1.0,
            "trailing_silence": 0.2,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "d8ab67c6-953d-4bd8-9370-8fa53a0f1453"

    def test_camb_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "camb", "tts")
        if not provider_id:
            pytest.skip("camb TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "camb_voice_uuid",
            "language": "en",
            "user_instructions": "Speak clearly and professionally",
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "camb_voice_uuid"

    def test_asyncai_http_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "asyncai_http", "tts")
        if not provider_id:
            pytest.skip("asyncai_http TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "13616e5f-6fda-4247-b548-8821cb71fb54",
            "language": "en",
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "13616e5f-6fda-4247-b548-8821cb71fb54"

    def test_aws_polly_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "aws_polly", "tts")
        if not provider_id:
            pytest.skip("aws_polly TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "Joanna",
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_session_token": "",
            "region": "us-east-1",
            "engine": "neural",
            "language": "en-US",
            "pitch": "medium",
            "rate": "medium",
            "volume": "medium",
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "Joanna"
        assert data["tts_metadata"]["engine"] == "neural"

    def test_google_base_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "google_base", "tts")
        if not provider_id:
            pytest.skip("google_base TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "en-US-Chirp3-HD-Achernar",
            "credentials": "",
            "credentials_path": "",
            "location": "global",
            "language": "en",
            "speaking_rate": 1.0,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "en-US-Chirp3-HD-Achernar"

    def test_azure_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "azure", "tts")
        if not provider_id:
            pytest.skip("azure TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "en-US-AvaMultilingualNeural",
            "region": "eastus",
            "emphasis": "moderate",
            "language": "en-US",
            "pitch": "medium",
            "rate": "medium",
            "role": "Girl",
            "style": "friendly",
            "style_degree": "1.0",
            "volume": "medium",
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "en-US-AvaMultilingualNeural"
        assert data["tts_metadata"]["style"] == "friendly"

    def test_speechmatics_tts(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "speechmatics", "tts")
        if not provider_id:
            pytest.skip("speechmatics TTS provider not found in DB")
        agent_id = _create_agent(client_as_member)
        tts_metadata = {
            "model_id": model_id,
            "voice_id": "speechmatics_voice_id",
            "sample_rate": 16000,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            tts_service_id=provider_id,
            tts_metadata=tts_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tts_metadata"]["voice_id"] == "speechmatics_voice_id"


# ─── S2S Provider Configs ───


class TestS2SProviderConfigs:
    """Test upsert_agent_config with Speech-to-Speech (S2S) provider metadata."""

    def test_openai_realtime_s2s(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "openai_realtime", "s2s")
        if not provider_id:
            pytest.skip("openai_realtime S2S provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "is_s2s": True,
            "voice_id": "alloy",
            "temperature": 0.8,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["is_s2s"] is True
        assert data["llm_metadata"]["voice_id"] == "alloy"
        assert data["llm_metadata"]["temperature"] == 0.8

    def test_gemini_live_s2s(self, client_as_member, db_session):
        provider_id, model_id = _resolve_provider(db_session, "gemini_live", "s2s")
        if not provider_id:
            pytest.skip("gemini_live S2S provider not found in DB")
        agent_id = _create_agent(client_as_member)
        llm_metadata = {
            "model_id": model_id,
            "is_s2s": True,
            "voice_id": "Puck",
            "temperature": 0.7,
        }
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=provider_id,
            llm_metadata=llm_metadata,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_metadata"]["is_s2s"] is True
        assert data["llm_metadata"]["voice_id"] == "Puck"
        assert data["llm_metadata"]["temperature"] == 0.7


# ─── Provider Switching ───


class TestProviderSwitching:
    """Test switching from one provider to another within the same agent config.

    NOTE: The upsert uses ON CONFLICT UPDATE with all updatable fields, so every
    call must send the complete config (all three service types). Fields not sent
    will be overwritten to NULL.
    """

    def test_switch_llm_openai_to_anthropic(self, client_as_member, db_session):
        """Switch LLM provider from OpenAI to Anthropic."""
        openai_pid, openai_mid = _resolve_provider(db_session, "openai", "llm")
        anthropic_pid, anthropic_mid = _resolve_provider(db_session, "anthropic", "llm")
        stt_pid, stt_mid = _resolve_provider(db_session, "deepgram", "stt")
        tts_pid, tts_mid = _resolve_provider(db_session, "cartesia", "tts")
        if not openai_pid:
            pytest.skip("openai LLM provider not found in DB")
        if not anthropic_pid:
            pytest.skip("anthropic LLM provider not found in DB")
        if not stt_pid or not tts_pid:
            pytest.skip("deepgram STT or cartesia TTS provider not found in DB")

        agent_id = _create_agent(client_as_member)

        # Create full pipeline with OpenAI LLM
        resp1 = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=openai_pid,
            llm_metadata={"model_id": openai_mid, "temperature": 0.7, "frequency_penalty": 0.5},
            stt_service_id=stt_pid,
            stt_metadata={"model_id": stt_mid, "sample_rate": 16000, "language": "en"},
            tts_service_id=tts_pid,
            tts_metadata={"model_id": tts_mid, "voice_id": "e07c00bc-4134-4eae-9ea4-1a55fb45746b", "language": "en"},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["llm_metadata"]["temperature"] == 0.7

        # Switch LLM to Anthropic — pass uuid so upsert can find the existing record
        resp2 = _upsert_config(
            client_as_member, agent_id,
            uuid=data1["uuid"],
            llm_service_id=anthropic_pid,
            llm_metadata={"model_id": anthropic_mid, "temperature": 0.9, "enable_prompt_caching": True, "max_tokens": 2048},
            stt_service_id=stt_pid,
            stt_metadata={"model_id": stt_mid, "sample_rate": 16000, "language": "en"},
            tts_service_id=tts_pid,
            tts_metadata={"model_id": tts_mid, "voice_id": "e07c00bc-4134-4eae-9ea4-1a55fb45746b", "language": "en"},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["llm_metadata"]["temperature"] == 0.9
        assert data2["llm_metadata"]["enable_prompt_caching"] is True
        assert data2["llm_service_id"] == anthropic_pid

    def test_switch_stt_deepgram_to_openai(self, client_as_member, db_session):
        """Switch STT provider from Deepgram to OpenAI."""
        llm_pid, llm_mid = _resolve_provider(db_session, "openai", "llm")
        dg_pid, dg_mid = _resolve_provider(db_session, "deepgram", "stt")
        oai_stt_pid, oai_stt_mid = _resolve_provider(db_session, "openai", "stt")
        tts_pid, tts_mid = _resolve_provider(db_session, "cartesia", "tts")
        if not llm_pid:
            pytest.skip("openai LLM provider not found in DB")
        if not dg_pid:
            pytest.skip("deepgram STT provider not found in DB")
        if not oai_stt_pid:
            pytest.skip("openai STT provider not found in DB")
        if not tts_pid:
            pytest.skip("cartesia TTS provider not found in DB")

        agent_id = _create_agent(client_as_member)

        # Create full pipeline with Deepgram STT
        resp1 = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=llm_pid,
            llm_metadata={"model_id": llm_mid, "temperature": 0.7},
            stt_service_id=dg_pid,
            stt_metadata={"model_id": dg_mid, "sample_rate": 16000, "language": "en"},
            tts_service_id=tts_pid,
            tts_metadata={"model_id": tts_mid, "voice_id": "e07c00bc-4134-4eae-9ea4-1a55fb45746b", "language": "en"},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["stt_metadata"]["language"] == "en"

        # Switch STT to OpenAI — pass uuid so upsert can find the existing record
        resp2 = _upsert_config(
            client_as_member, agent_id,
            uuid=data1["uuid"],
            llm_service_id=llm_pid,
            llm_metadata={"model_id": llm_mid, "temperature": 0.7},
            stt_service_id=oai_stt_pid,
            stt_metadata={"model_id": oai_stt_mid, "language": "en", "prompt": "Transcribe support calls", "temperature": 0.0},
            tts_service_id=tts_pid,
            tts_metadata={"model_id": tts_mid, "voice_id": "e07c00bc-4134-4eae-9ea4-1a55fb45746b", "language": "en"},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["stt_metadata"]["prompt"] == "Transcribe support calls"
        assert data2["stt_service_id"] == oai_stt_pid

    def test_switch_tts_cartesia_to_elevenlabs(self, client_as_member, db_session):
        """Switch TTS provider from Cartesia to ElevenLabs."""
        llm_pid, llm_mid = _resolve_provider(db_session, "openai", "llm")
        stt_pid, stt_mid = _resolve_provider(db_session, "deepgram", "stt")
        cart_pid, cart_mid = _resolve_provider(db_session, "cartesia", "tts")
        el_pid, el_mid = _resolve_provider(db_session, "elevenlabs", "tts")
        if not llm_pid or not stt_pid:
            pytest.skip("openai LLM or deepgram STT provider not found in DB")
        if not cart_pid:
            pytest.skip("cartesia TTS provider not found in DB")
        if not el_pid:
            pytest.skip("elevenlabs TTS provider not found in DB")

        agent_id = _create_agent(client_as_member)

        # Create full pipeline with Cartesia TTS
        resp1 = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=llm_pid,
            llm_metadata={"model_id": llm_mid, "temperature": 0.7},
            stt_service_id=stt_pid,
            stt_metadata={"model_id": stt_mid, "sample_rate": 16000, "language": "en"},
            tts_service_id=cart_pid,
            tts_metadata={"model_id": cart_mid, "voice_id": "e07c00bc-4134-4eae-9ea4-1a55fb45746b", "language": "en", "speed": "normal"},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()

        # Switch TTS to ElevenLabs — pass uuid so upsert can find the existing record
        resp2 = _upsert_config(
            client_as_member, agent_id,
            uuid=data1["uuid"],
            llm_service_id=llm_pid,
            llm_metadata={"model_id": llm_mid, "temperature": 0.7},
            stt_service_id=stt_pid,
            stt_metadata={"model_id": stt_mid, "sample_rate": 16000, "language": "en"},
            tts_service_id=el_pid,
            tts_metadata={"model_id": el_mid, "voice_id": "CwhRBWXzGAHq8TQ4Fs17", "language": "en", "stability": 0.5, "similarity_boost": 0.75},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["tts_metadata"]["voice_id"] == "CwhRBWXzGAHq8TQ4Fs17"
        assert data2["tts_metadata"]["stability"] == 0.5
        assert data2["tts_service_id"] == el_pid


# ─── Combined Pipeline ───


class TestCombinedPipeline:
    """Test setting LLM + STT + TTS together in a single request."""

    def test_full_pipeline_openai_deepgram_cartesia(self, client_as_member, db_session):
        """Full pipeline: OpenAI LLM + Deepgram STT + Cartesia TTS."""
        llm_pid, llm_mid = _resolve_provider(db_session, "openai", "llm")
        stt_pid, stt_mid = _resolve_provider(db_session, "deepgram", "stt")
        tts_pid, tts_mid = _resolve_provider(db_session, "cartesia", "tts")
        if not llm_pid:
            pytest.skip("openai LLM provider not found in DB")
        if not stt_pid:
            pytest.skip("deepgram STT provider not found in DB")
        if not tts_pid:
            pytest.skip("cartesia TTS provider not found in DB")

        agent_id = _create_agent(client_as_member)
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=llm_pid,
            llm_metadata={
                "model_id": llm_mid,
                "temperature": 0.7,
                "frequency_penalty": 0.5,
                "presence_penalty": 0.3,
                "max_completion_tokens": 2048,
            },
            stt_service_id=stt_pid,
            stt_metadata={
                "model_id": stt_mid,
                "sample_rate": 16000,
                "language": "en",
            },
            tts_service_id=tts_pid,
            tts_metadata={
                "model_id": tts_mid,
                "voice_id": "e07c00bc-4134-4eae-9ea4-1a55fb45746b",
                "language": "en",
                "speed": "normal",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_service_id"] == llm_pid
        assert data["stt_service_id"] == stt_pid
        assert data["tts_service_id"] == tts_pid
        assert data["llm_metadata"]["temperature"] == 0.7
        assert data["stt_metadata"]["language"] == "en"
        assert data["tts_metadata"]["voice_id"] == "e07c00bc-4134-4eae-9ea4-1a55fb45746b"

    def test_mixed_pipeline_anthropic_openai_elevenlabs(self, client_as_member, db_session):
        """Mixed pipeline: Anthropic LLM + OpenAI STT + ElevenLabs TTS."""
        llm_pid, llm_mid = _resolve_provider(db_session, "anthropic", "llm")
        stt_pid, stt_mid = _resolve_provider(db_session, "openai", "stt")
        tts_pid, tts_mid = _resolve_provider(db_session, "elevenlabs", "tts")
        if not llm_pid:
            pytest.skip("anthropic LLM provider not found in DB")
        if not stt_pid:
            pytest.skip("openai STT provider not found in DB")
        if not tts_pid:
            pytest.skip("elevenlabs TTS provider not found in DB")

        agent_id = _create_agent(client_as_member)
        resp = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=llm_pid,
            llm_metadata={
                "model_id": llm_mid,
                "temperature": 0.7,
                "enable_prompt_caching": True,
                "max_tokens": 1024,
                "top_k": 40,
                "top_p": 0.9,
            },
            stt_service_id=stt_pid,
            stt_metadata={
                "model_id": stt_mid,
                "language": "en",
                "prompt": "Transcribe customer support calls",
                "temperature": 0.0,
            },
            tts_service_id=tts_pid,
            tts_metadata={
                "model_id": tts_mid,
                "voice_id": "CwhRBWXzGAHq8TQ4Fs17",
                "language": "en",
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.5,
                "use_speaker_boost": True,
                "speed": 1.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_service_id"] == llm_pid
        assert data["stt_service_id"] == stt_pid
        assert data["tts_service_id"] == tts_pid
        assert data["llm_metadata"]["enable_prompt_caching"] is True
        assert data["stt_metadata"]["prompt"] == "Transcribe customer support calls"
        assert data["tts_metadata"]["stability"] == 0.5


# ─── Provider Metadata Update ───


class TestProviderMetadataUpdate:
    """Test updating metadata values within the same provider.

    NOTE: The upsert uses ON CONFLICT UPDATE with all updatable fields, so every
    call must send the complete config (all three service types). Fields not sent
    will be overwritten to NULL.
    """

    def test_update_openai_llm_temperature(self, client_as_member, db_session):
        """Create config with OpenAI LLM temp=0.7, update to temp=0.9."""
        llm_pid, llm_mid = _resolve_provider(db_session, "openai", "llm")
        stt_pid, stt_mid = _resolve_provider(db_session, "deepgram", "stt")
        tts_pid, tts_mid = _resolve_provider(db_session, "cartesia", "tts")
        if not llm_pid:
            pytest.skip("openai LLM provider not found in DB")
        if not stt_pid or not tts_pid:
            pytest.skip("deepgram STT or cartesia TTS provider not found in DB")

        agent_id = _create_agent(client_as_member)

        # Create full pipeline with temperature 0.7
        resp1 = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=llm_pid,
            llm_metadata={"model_id": llm_mid, "temperature": 0.7, "frequency_penalty": 0.5},
            stt_service_id=stt_pid,
            stt_metadata={"model_id": stt_mid, "sample_rate": 16000, "language": "en"},
            tts_service_id=tts_pid,
            tts_metadata={"model_id": tts_mid, "voice_id": "e07c00bc-4134-4eae-9ea4-1a55fb45746b", "language": "en"},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["llm_metadata"]["temperature"] == 0.7

        # Update temperature to 0.9 — pass uuid so upsert can find the existing record
        resp2 = _upsert_config(
            client_as_member, agent_id,
            uuid=data1["uuid"],
            llm_service_id=llm_pid,
            llm_metadata={"model_id": llm_mid, "temperature": 0.9, "frequency_penalty": 0.5},
            stt_service_id=stt_pid,
            stt_metadata={"model_id": stt_mid, "sample_rate": 16000, "language": "en"},
            tts_service_id=tts_pid,
            tts_metadata={"model_id": tts_mid, "voice_id": "e07c00bc-4134-4eae-9ea4-1a55fb45746b", "language": "en"},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["llm_metadata"]["temperature"] == 0.9

    def test_update_deepgram_stt_language(self, client_as_member, db_session):
        """Create config with Deepgram STT language=en, update to language=es."""
        llm_pid, llm_mid = _resolve_provider(db_session, "openai", "llm")
        stt_pid, stt_mid = _resolve_provider(db_session, "deepgram", "stt")
        tts_pid, tts_mid = _resolve_provider(db_session, "cartesia", "tts")
        if not stt_pid:
            pytest.skip("deepgram STT provider not found in DB")
        if not llm_pid or not tts_pid:
            pytest.skip("openai LLM or cartesia TTS provider not found in DB")

        agent_id = _create_agent(client_as_member)

        # Create full pipeline with language en
        resp1 = _upsert_config(
            client_as_member, agent_id,
            llm_service_id=llm_pid,
            llm_metadata={"model_id": llm_mid, "temperature": 0.7},
            stt_service_id=stt_pid,
            stt_metadata={"model_id": stt_mid, "sample_rate": 16000, "language": "en"},
            tts_service_id=tts_pid,
            tts_metadata={"model_id": tts_mid, "voice_id": "e07c00bc-4134-4eae-9ea4-1a55fb45746b", "language": "en"},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["stt_metadata"]["language"] == "en"

        # Update language to es — pass uuid so upsert can find the existing record
        resp2 = _upsert_config(
            client_as_member, agent_id,
            uuid=data1["uuid"],
            llm_service_id=llm_pid,
            llm_metadata={"model_id": llm_mid, "temperature": 0.7},
            stt_service_id=stt_pid,
            stt_metadata={"model_id": stt_mid, "sample_rate": 16000, "language": "es"},
            tts_service_id=tts_pid,
            tts_metadata={"model_id": tts_mid, "voice_id": "e07c00bc-4134-4eae-9ea4-1a55fb45746b", "language": "en"},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["stt_metadata"]["language"] == "es"
