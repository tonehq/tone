import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class InfisicalConfigError(RuntimeError):
    pass


def get_infisical_secrets() -> dict:
    token = os.getenv("INFISICAL_TOKEN")
    project_id = os.getenv("INFISICAL_PROJECT_ID")

    if not token or not project_id:
        return {}

    environment = os.getenv("INFISICAL_ENV", os.getenv("ENV", "dev"))
    host = os.getenv("INFISICAL_HOST", "https://secrets.trytone.ai")
    source = f"host={host} project_id={project_id} environment={environment}"

    try:
        from infisical_sdk import InfisicalSDKClient
    except ImportError as exc:
        raise InfisicalConfigError(
            "INFISICAL_TOKEN and INFISICAL_PROJECT_ID are set but the "
            "'infisical_sdk' package is not installed. Install it or unset "
            "those variables to fall back to .env."
        ) from exc

    try:
        client = InfisicalSDKClient(host=host, token=token)
        secrets_response = client.secrets.list_secrets(
            project_id=project_id,
            environment_slug=environment,
            secret_path="/",
        )
    except Exception as exc:
        raise InfisicalConfigError(
            f"Failed to load secrets from Infisical ({source}). "
            f"Check INFISICAL_TOKEN, INFISICAL_PROJECT_ID and INFISICAL_ENV. "
            f"Underlying error: {exc}"
        ) from exc

    secrets = {
        secret.secretKey: secret.secretValue
        for secret in secrets_response.secrets
    }

    if not secrets:
        raise InfisicalConfigError(
            f"Infisical returned no secrets ({source}). The project, "
            f"environment slug or secret path is probably wrong."
        )

    return secrets


class Settings:
    def __init__(self):
        infisical_secrets = get_infisical_secrets()

        def get_secret(key: str, default: str = "") -> str:
            return infisical_secrets.get(key) or os.getenv(key, default)

        self.DATABASE_URL: str = get_secret("DATABASE_URL")
        self.JWT_SECRET_KEY: str = get_secret("JWT_SECRET_KEY", "your-secret-key-here")
        self.JWT_ALGORITHM: str = "HS256"
        self.ACCESS_TOKEN_EXPIRE_HOURS: int = 24
        self.REFRESH_TOKEN_EXPIRE_DAYS: int = 30
        

        self.ENVIRONMENT: str = get_secret("ENV", "development")

        # ── Auth cookies (httpOnly access/refresh token transport) ──────────
        # Tokens ride in httpOnly cookies instead of JS-readable storage so an
        # XSS hole can't exfiltrate a session. In prod the frontend + API share
        # a parent domain (e.g. app.trytone.ai + api.trytone.ai), so setting
        # COOKIE_DOMAIN=.trytone.ai scopes one cookie to both. Left blank the
        # cookie is host-only (correct for a single-origin dev proxy).
        _cookie_env = self.ENVIRONMENT.lower()
        _cookie_is_local = _cookie_env in ("development", "dev", "local", "test")
        self.COOKIE_DOMAIN: str = get_secret("COOKIE_DOMAIN", "")
        self.COOKIE_SECURE: bool = get_secret(
            "COOKIE_SECURE", "false" if _cookie_is_local else "true"
        ).lower() == "true"
        # One of "lax" | "strict" | "none". "none" REQUIRES COOKIE_SECURE=true.
        self.COOKIE_SAMESITE: str = get_secret("COOKIE_SAMESITE", "lax").lower()

        # ── CORS (credentialed requests can't use a wildcard origin) ────────
        # Browsers reject `Access-Control-Allow-Origin: *` together with
        # credentials, so we reflect an explicit allow-list. CORS_ALLOW_ORIGINS
        # is an exact comma-separated list (local dev); CORS_ALLOW_ORIGIN_REGEX
        # covers every *.trytone.ai subdomain in deployed envs.
        self.CORS_ALLOW_ORIGINS: list = [
            o.strip()
            for o in get_secret(
                "CORS_ALLOW_ORIGINS", "http://localhost:3000,http://localhost:3001"
            ).split(",")
            if o.strip()
        ]
        self.CORS_ALLOW_ORIGIN_REGEX: str = get_secret(
            "CORS_ALLOW_ORIGIN_REGEX", r"https://([a-z0-9-]+\.)*trytone\.ai"
        )

        self.POD_PINNING_ENABLED: bool = get_secret("POD_PINNING_ENABLED", "false").lower() == "true"
        # Telephony-free WebSocket test endpoint (/ws/test). Runs a real, paid
        # LLM/STT/TTS pipeline and takes no auth, so it is OFF by default and should
        # stay off in production — enable only in dev/staging for agent testing.
        self.ENABLE_WS_TEST_ENDPOINT: bool = get_secret("ENABLE_WS_TEST_ENDPOINT", "false").lower() == "true"
        self.CALL_SERVER_HOST: str = get_secret("CALL_SERVER_HOST", "")
        self.CALL_WORKER_PREFIX: str = get_secret("CALL_WORKER_PREFIX", "tone-call-worker")
        self.POD_SYNC_NAMESPACE: str = get_secret("POD_SYNC_NAMESPACE", "staging")
        # Dedicated OUTBOUND voice-pod pool (WebSocket "test bridge" trigger runs its media here,
        # NOT on the API/orchestrator pod — see WebSocketCallEngine). The originator picks a pod
        # from this StatefulSet (via PodPicker over this prefix) and hands the bridge off over the
        # StatefulSet's headless service (intra-cluster, no ingress) at ``{pod}.{headless}.{ns}.svc``.
        self.OUTBOUND_CALL_WORKER_PREFIX: str = get_secret(
            "OUTBOUND_CALL_WORKER_PREFIX", "tone-outbound-call-worker"
        )
        self.OUTBOUND_CALL_HEADLESS_SERVICE: str = get_secret(
            "OUTBOUND_CALL_HEADLESS_SERVICE", "tone-outbound-call-headless"
        )
        self.OUTBOUND_CALL_WORKER_PORT: int = int(get_secret("OUTBOUND_CALL_WORKER_PORT", "8080"))
        # Per voice-pod concurrent-call ceiling, enforced at the pod's ws-bridge-start route
        # (429 when full → the originator queues the overflow). 0/<=0 = unlimited. Set on the
        # call-worker manifests; previously an unread env var, now honoured in code.
        self.MAX_CONCURRENT_CALLS: int = int(get_secret("MAX_CONCURRENT_CALLS", "2"))
        # Optional shared secret for the intra-cluster ws-bridge-start hand-off. Empty = no check
        # (same trust model as /ws — the route is not exposed via any ingress). When set, the
        # originator sends it and the pod requires it.
        self.WS_BRIDGE_INTERNAL_TOKEN: str = get_secret("WS_BRIDGE_INTERNAL_TOKEN", "")

        # Public base URL (scheme + host, no /api/v1) that Twilio can reach for
        # outbound-call TwiML + status callbacks. Root-mounted telephony routes hang
        # off this (e.g. {BASE_CALL_URL}/twiml/outbound). Required for outbound dialing;
        # scheduled dials run in the worker with no request context to derive it from.
        # Locally: an ngrok URL. Prod: the public API host.
        self.BASE_CALL_URL: str = get_secret("BASE_CALL_URL", "").rstrip("/")

        # WebSocket call trigger (provider="websocket"): the outbound call is bridged over a
        # WebSocket client to a REMOTE deployment's /ws/test endpoint (agent-to-agent, no PSTN),
        # instead of Twilio placing a phone call. WS_CALL_TARGET_URL is that remote's base
        # (scheme + host, e.g. wss://staging-test.trytone.ai) — required; empty disables the WS
        # trigger. The remote agent is normally resolved by the dialed to_number on that side
        # (like a real call); WS_CALL_TARGET_AGENT_ID is an OPTIONAL fallback used only when a
        # call carries no number to route on.
        self.WS_CALL_TARGET_URL: str = get_secret("WS_CALL_TARGET_URL", "").rstrip("/")
        self.WS_CALL_TARGET_AGENT_ID: str = get_secret("WS_CALL_TARGET_AGENT_ID", "")
        # Single-process / local-dev escape hatch. The WS bridge is normally handed off to a
        # dedicated outbound-call-worker pod (keeps media OFF the API/orchestrator pod). When no such
        # pod is registered — e.g. a local `uvicorn main:app` with no WORKER_MODE=voice sibling —
        # PodPicker.for_outbound finds nothing and the row would hold forever. With this flag ON the
        # originator runs the bridge IN-PROCESS instead. OFF by default so staging/prod keep the pod
        # hand-off; set true only for local/single-node runs.
        self.WS_BRIDGE_ALLOW_INLINE: bool = (
            get_secret("WS_BRIDGE_ALLOW_INLINE", "false").lower() == "true"
        )
        # NB: access to the WebSocket ("test bridge") trigger is limited to users whose
        # ``members.role == 'super_admin'`` — see OutboundCallService.is_ws_trigger_allowed. The
        # role is assigned via SQL only (no UI/API), so the allowlist changes without a redeploy.


        self.APPLICATION_URL: str = get_secret("APPLICATION_URL", "http://localhost:3000")
        self.RESEND_API_KEY: str = get_secret("RESEND_API_KEY", "")

        self.LICENSE_KEY: Optional[str] = get_secret("TONE_LICENSE_KEY") or None
        self.SKIP_LICENSE_CHECK: bool = get_secret("SKIP_LICENSE_CHECK", "false").lower() == "true"

        self.DEFAULT_ORG_ID: str = get_secret("DEFAULT_ORG_ID", "00000000-0000-0000-0000-000000000001")

        # Auth token for scripts/API calls
        self.AUTH_TOKEN: str = get_secret("AUTH_TOKEN", "")

        # Base API URL for scripts
        self.BASE_API_URL: str = get_secret("BASE_API_URL", "http://localhost:8000/api/v1")

        # Redis
        self.REDIS_URL: str = get_secret("REDIS_URL", "redis://localhost:6379/0")

        # Logging. LOG_LEVEL is the baseline level every process boots at. For calls,
        # a finer level can be set per organization / per agent in the DB
        # (agents.log_level > organizations.log_level > this env baseline) — resolved by
        # core/services/log_level_resolver.py. Blank/invalid falls back to INFO.
        self.LOG_LEVEL: str = get_secret("LOG_LEVEL", "INFO")

        # Cloudflare R2 storage
        self.R2_ACCESS_KEY_ID: str = get_secret("R2_ACCESS_KEY_ID", "")
        self.R2_SECRET_ACCESS_KEY: str = get_secret("R2_SECRET_ACCESS_KEY", "")
        self.R2_BUCKET_NAME: str = get_secret("R2_BUCKET_NAME", "")
        self.R2_ENDPOINT_URL: str = get_secret("R2_ENDPOINT_URL", "")

        # Google OAuth
        self.GOOGLE_CLIENT_ID: str = get_secret("GOOGLE_CLIENT_ID", "")
        self.GOOGLE_CLIENT_SECRET: str = get_secret("GOOGLE_CLIENT_SECRET", "")

        # Pre-registered OAuth clients for MCP servers that don't support Dynamic Client
        # Registration (RFC 7591). HubSpot's official MCP server (mcp.hubspot.com) requires
        # creating an "MCP Auth App" in the HubSpot developer portal to obtain these.
        self.HUBSPOT_MCP_CLIENT_ID: str = get_secret("HUBSPOT_MCP_CLIENT_ID", "")
        self.HUBSPOT_MCP_CLIENT_SECRET: str = get_secret("HUBSPOT_MCP_CLIENT_SECRET", "")

        self.SALESFORCE_CLIENT_ID: str = get_secret("SALESFORCE_CLIENT_ID", "")
        self.SALESFORCE_CLIENT_SECRET: str = get_secret("SALESFORCE_CLIENT_SECRET", "")
        self.SALESFORCE_MY_DOMAIN: str = get_secret("SALESFORCE_MY_DOMAIN", "")

        self.LLAMA_CLOUD_API_KEY: str = get_secret("LLAMA_CLOUD_API_KEY", "")

        # Global OpenAI key used as a fallback for AI helper features (e.g. system-prompt
        # generation) when an org hasn't configured its own provider key.
        self.OPENAI_API_KEY: str = get_secret("OPENAI_API_KEY", "")

        self.LIVEKIT_URL: str = get_secret("LIVEKIT_URL", "")
        self.LIVEKIT_API_KEY: str = get_secret("LIVEKIT_API_KEY", "")
        self.LIVEKIT_API_SECRET: str = get_secret("LIVEKIT_API_SECRET", "")
        self.DAILY_API_KEY: str = get_secret("DAILY_API_KEY", "")
        self.WEBRTC_CLIENT_BASE_URL: str = get_secret("WEBRTC_CLIENT_BASE_URL", "")
        self.CALL_WORKER_INTERNAL_URL: str = get_secret("CALL_WORKER_INTERNAL_URL", "")

        self.SEND_SMS_DEFAULT_TO_NUMBER: str = get_secret("SEND_SMS_DEFAULT_TO_NUMBER", "")

        # ── Grafana Loki (log egress + per-call read-back) ──────────────────
        # LOKI_URL/LOKI_USER/GRAFANA_API_KEY are the same secrets the Alloy
        # DaemonSet uses to PUSH logs to Grafana Cloud (see the monitoring
        # manifests). We surface them here so the per-call log sync can READ a
        # finished call's lines back out of Loki. All blank in local dev, which
        # makes loki_read_configured() False and the sync a safe no-op.
        self.LOKI_URL: str = get_secret("LOKI_URL", "")  # push endpoint (…/loki/api/v1/push)
        self.LOKI_USER: str = get_secret("LOKI_USER", "")
        self.GRAFANA_API_KEY: str = get_secret("GRAFANA_API_KEY", "")

        # Query endpoint for reading logs back. Defaults to deriving from the
        # push URL (swap the trailing /push for /query_range) so a single
        # LOKI_URL secret configures both directions; override explicitly when
        # the Grafana Cloud query host differs from the push host.
        self.LOKI_QUERY_URL: str = (
            get_secret("LOKI_QUERY_URL", "")
            or (self.LOKI_URL.replace("/loki/api/v1/push", "/loki/api/v1/query_range") if self.LOKI_URL else "")
        )
        # Read creds default to the push creds; override if a dedicated
        # read-scoped (logs:read) token is provisioned.
        self.LOKI_QUERY_USER: str = get_secret("LOKI_QUERY_USER", "") or self.LOKI_USER
        self.LOKI_QUERY_TOKEN: str = get_secret("LOKI_QUERY_TOKEN", "") or self.GRAFANA_API_KEY

        # Per-call sync tuning. No enable/disable flag — the post-call action is
        # always wired; loki_read_configured() alone gates it.
        # Loki stream selector for the per-call log fetch — the trace_id line
        # filter does the real per-call scoping; this just narrows the streams.
        # Set LOKI_SYNC_APP_LABEL to a single workload (builds {app="<value>"}),
        # e.g. staging-tone-call-worker. Left blank, the query falls back to the
        # env-agnostic {component=~"call|api"} (Alloy labels tone pods with
        # component={call,api,worker}). NOTE: there is no app="tone" label — app
        # values are the workload names, which is why the old default matched
        # nothing.
        self.LOKI_SYNC_APP_LABEL: str = get_secret("LOKI_SYNC_APP_LABEL", "").strip()
        self.LOKI_SYNC_DELAY_SECONDS: int = int(get_secret("LOKI_SYNC_DELAY_SECONDS", "120"))
        self.LOKI_SYNC_PRE_BUFFER_SECONDS: int = int(get_secret("LOKI_SYNC_PRE_BUFFER_SECONDS", "30"))
        self.LOKI_SYNC_POST_BUFFER_SECONDS: int = int(get_secret("LOKI_SYNC_POST_BUFFER_SECONDS", "60"))
        self.LOKI_SYNC_PAGE_LIMIT: int = int(get_secret("LOKI_SYNC_PAGE_LIMIT", "5000"))
        self.LOKI_SYNC_MAX_PAGES: int = int(get_secret("LOKI_SYNC_MAX_PAGES", "50"))
        self.LOKI_SYNC_HTTP_TIMEOUT: int = int(get_secret("LOKI_SYNC_HTTP_TIMEOUT", "30"))
        self.LOKI_SYNC_MAX_RETRIES: int = int(get_secret("LOKI_SYNC_MAX_RETRIES", "5"))

        # Per-batch outbound concurrency knob — the UI "Concurrent calls" selector's upper
        # bound AND the default limit a batch gets when it doesn't request one. NOT a global
        # in-flight ceiling: the limit is enforced per scheduling batch (rows sharing a
        # ``batch_id``), so N concurrent batches can each run up to this many at once. 0
        # (default) = unset: the selector has no cap and a batch with no requested value runs
        # with no per-batch limit. See core/services/outbound_capacity.py for the resolver.
        self.MAX_CONCURRENT_OUTBOUND_CALLS: int = int(get_secret("MAX_CONCURRENT_OUTBOUND_CALLS", "0"))
        # Cap for the OUTBOUND best-effort background thread pools — pipeline cache pre-warming
        # (after a dial, while it rings) and the completion refill (enqueueing a batch's next
        # call off the status webhook). 0 (default) = ON-DEMAND: no threads are held idle; one
        # is created at call time only when needed, up to the runtime's default cap. Set > 0 to
        # pin an explicit ceiling. Kept as a knob for future tuning.
        self.OUTBOUND_BG_WORKERS: int = int(get_secret("OUTBOUND_BG_WORKERS", "0"))

        # ── RAG ingestion defaults ──────────────────────────────────────────
        # Baseline parser / tokeniser / embedder / vector-store used when a
        # caller doesn't supply an override. Every value maps to a registry
        # entry (see core/services/rag/parser_factory.py, tokeniser_factory.py,
        # embedder_factory.py, factory.py). Consumed only by
        # IngestionRunService.resolve_run_config — no other file bakes these in.
        self.DEFAULT_PARSER: str = get_secret("DEFAULT_PARSER", "docling")
        self.DEFAULT_TOKENISER: str = get_secret("DEFAULT_TOKENISER", "docling_hybrid")
        self.DEFAULT_EMBEDDING_PROVIDER: str = get_secret("DEFAULT_EMBEDDING_PROVIDER", "openai")
        self.DEFAULT_EMBEDDING_MODEL: str = get_secret("DEFAULT_EMBEDDING_MODEL", "text-embedding-3-small")
        self.DEFAULT_EMBEDDING_DIMENSIONS: int = int(get_secret("DEFAULT_EMBEDDING_DIMENSIONS", "1536"))
        self.DEFAULT_VECTOR_STORE: str = get_secret("DEFAULT_VECTOR_STORE", "pgvector")

        # Pinecone vector store — API key for the "pinecone" backend in the RAG
        # store factory. Empty in envs that only use pgvector; the store itself
        # raises EmbeddingProviderUnavailableError if a run requests pinecone
        # without a key configured.
        self.PINECONE_API_KEY: str = get_secret("PINECONE_API_KEY", "")

        # ── RAG evaluation harness ──────────────────────────────────────────
        # Auto-runs after every successful ingestion (IngestionRunService.complete_run
        # enqueues eval_ingestion_run when EVAL_AUTO_RUN_ENABLED is true). All
        # eval knobs live here — no other file bakes them in.
        self.EVAL_AUTO_RUN_ENABLED: bool = get_secret("EVAL_AUTO_RUN_ENABLED", "true").lower() == "true"
        self.EVAL_GENERATION_MODEL: str = get_secret("EVAL_GENERATION_MODEL", "gpt-4o")
        self.EVAL_ANSWER_MODEL: str = get_secret("EVAL_ANSWER_MODEL", "gpt-4o")
        self.EVAL_JUDGE_MODEL: str = get_secret("EVAL_JUDGE_MODEL", "gpt-4o")
        self.EVAL_TOP_K: int = int(get_secret("EVAL_TOP_K", "8"))
        self.EVAL_MAX_CONTEXT_CHARS: int = int(get_secret("EVAL_MAX_CONTEXT_CHARS", "60000"))

    def loki_read_configured(self) -> bool:
        """True only when we have enough to read a call's logs back from Loki.

        The single guard for the whole feature: when False (e.g. local dev with
        no Loki secrets), the post-call action, worker job and manual endpoint
        all no-op instead of erroring."""
        return bool(self.LOKI_QUERY_URL and self.LOKI_QUERY_TOKEN)


settings = Settings()
