import os
from typing import Optional
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


# ── Environment classification ──────────────────────────────────────────────
# Names we treat as "developer laptop / CI" — Tier B (deployed-only) keys are
# NOT required in these envs. Everything else (staging, production, uat, …) is
# treated as deployed and must supply the full set.
DEV_ENV_NAMES = frozenset({"dev", "development", "local", "test"})

# ── Mandatory env vars (missing = pod refuses to start) ─────────────────────
# Strict env-only policy (see .env.example). Every setting whose absence would
# cause runtime failure or a wrong-by-default behavior is listed here — nothing
# in this module carries a code-side fallback. Keys where empty is a legitimate
# "off / disabled" value (bool flags that default to false; concurrency knobs
# whose comments say 0 = unlimited/on-demand) intentionally stay OFF this list.

# Tier A — required in EVERY env, including dev.
MANDATORY_KEYS: tuple[str, ...] = (
    # Core auth + identity
    "DATABASE_URL",
    "JWT_SECRET_KEY",
    "ENV",
    "DEFAULT_ORG_ID",
    "LOG_LEVEL",
    # HTTP surface
    "COOKIE_SAMESITE",
    "CORS_ALLOW_ORIGINS",
    "CORS_ALLOW_ORIGIN_REGEX",
    "APPLICATION_URL",
    "BASE_API_URL",
    # Call/worker routing (non-zero ints or non-empty strings required)
    "CALL_WORKER_PREFIX",
    "OUTBOUND_CALL_WORKER_PREFIX",
    "OUTBOUND_CALL_HEADLESS_SERVICE",
    "OUTBOUND_CALL_WORKER_PORT",
    "POD_SYNC_NAMESPACE",
    "MAX_CONCURRENT_CALLS",
    # Loki per-call sync tuning (int knobs — empty would ValueError on int())
    "LOKI_SYNC_DELAY_SECONDS",
    "LOKI_SYNC_PRE_BUFFER_SECONDS",
    "LOKI_SYNC_POST_BUFFER_SECONDS",
    "LOKI_SYNC_PAGE_LIMIT",
    "LOKI_SYNC_MAX_PAGES",
    "LOKI_SYNC_HTTP_TIMEOUT",
    "LOKI_SYNC_MAX_RETRIES",
    # RAG defaults — every value maps to a registry entry
    "DEFAULT_PARSER",
    "DEFAULT_TOKENISER",
    "DEFAULT_EMBEDDING_PROVIDER",
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_EMBEDDING_DIMENSIONS",
    "DEFAULT_VECTOR_STORE",
    # RAG eval harness
    "EVAL_AUTO_RUN_ENABLED",
    "EVAL_GENERATION_MODEL",
    "EVAL_ANSWER_MODEL",
    "EVAL_JUDGE_MODEL",
    "EVAL_TOP_K",
    "EVAL_MAX_CONTEXT_CHARS",
    "EVAL_JUDGE_ENGINE",
    "EVAL_METRIC_THRESHOLD",
    "EVAL_METRICS_ENABLED",
    # Agent LLM eval harness (dev/QA per-agent LLM-output scoring)
    "AGENT_LLM_EVAL_METRICS_ENABLED",
)

# Tier B — additionally required when ENV is not one of DEV_ENV_NAMES.
MANDATORY_PROD_KEYS: tuple[str, ...] = (
    "INFISICAL_TOKEN",
    "INFISICAL_PROJECT_ID",
    "REDIS_URL",
    "LOKI_URL",
    "GRAFANA_API_KEY",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
    "R2_ENDPOINT_URL",
    "BASE_CALL_URL",
)

# Values we treat as "unset" even when the string is non-empty — the historical
# in-code placeholder should never satisfy a mandatory check.
INSECURE_PLACEHOLDERS: dict[str, set[str]] = {
    "JWT_SECRET_KEY": {"your-secret-key-here"},
    "REDIS_URL": {"redis://localhost:6379/0"},
}


def _int_env(raw: str) -> int:
    """int() that treats empty string as 0.

    Import-safety only: keeps ``int(get_secret("K"))`` from crashing before
    ``_validate_required`` runs. Missing values that MUST be present are
    caught by the validator afterwards; 0 is a legitimate value for the
    knobs left off ``MANDATORY_KEYS`` (e.g. MAX_CONCURRENT_OUTBOUND_CALLS,
    OUTBOUND_BG_WORKERS — see comments below).
    """
    return int(raw) if raw else 0


def _bool_env(raw: str) -> bool:
    """Truthy string ("true", case-insensitive) → True; empty/anything else → False."""
    return (raw or "").strip().lower() == "true"


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

        # Raw (pre-coercion) values keyed by env name. The validator inspects
        # this dict so it can tell "unset" from a legitimate 0 / False /
        # empty-list value that a Settings attribute might not distinguish.
        self._raw: dict[str, str] = {}

        def get_secret(key: str) -> str:
            value = infisical_secrets.get(key) or os.getenv(key, "")
            self._raw[key] = value
            return value

        self.DATABASE_URL: str = get_secret("DATABASE_URL")
        self.JWT_SECRET_KEY: str = get_secret("JWT_SECRET_KEY")
        self.JWT_ALGORITHM: str = "HS256"
        self.ACCESS_TOKEN_EXPIRE_HOURS: int = 24
        self.REFRESH_TOKEN_EXPIRE_DAYS: int = 30

        self.ENVIRONMENT: str = get_secret("ENV")

        # ── Auth cookies (httpOnly access/refresh token transport) ──────────
        # Tokens ride in httpOnly cookies instead of JS-readable storage so an
        # XSS hole can't exfiltrate a session. In prod the frontend + API share
        # a parent domain (e.g. app.trytone.ai + api.trytone.ai), so setting
        # COOKIE_DOMAIN=.trytone.ai scopes one cookie to both. Left blank the
        # cookie is host-only (correct for a single-origin dev proxy).
        # "Am I running on a developer's laptop?" is a HOST question, not a
        # secrets-source question — read it straight from the local .env (via
        # os.getenv) so it isn't overwritten by whatever ENV value Infisical
        # happens to inject.
        _local_env = (os.getenv("ENV") or self.ENVIRONMENT or "").lower()
        _cookie_is_local = _local_env in DEV_ENV_NAMES
        self.COOKIE_DOMAIN: str = get_secret("COOKIE_DOMAIN")
        self.COOKIE_SECURE: bool = _bool_env(get_secret("COOKIE_SECURE"))
        # Local dev safety net: when a laptop is pointed at a staging Infisical
        # env, the pulled cookie values (Domain=.trytone.ai; Secure) get baked
        # into every Set-Cookie and the browser silently drops them on
        # http://localhost. Force host-only + non-Secure here so a
        # mis-configured secret source never locks a developer out.
        # Deployed envs (ENV=production/staging in the OS env) are untouched.
        if _cookie_is_local:
            self.COOKIE_DOMAIN = ""
            self.COOKIE_SECURE = False
        # One of "lax" | "strict" | "none". "none" REQUIRES COOKIE_SECURE=true.
        self.COOKIE_SAMESITE: str = get_secret("COOKIE_SAMESITE").lower()

        # ── CORS (credentialed requests can't use a wildcard origin) ────────
        # Browsers reject `Access-Control-Allow-Origin: *` together with
        # credentials, so we reflect an explicit allow-list. CORS_ALLOW_ORIGINS
        # is an exact comma-separated list (local dev); CORS_ALLOW_ORIGIN_REGEX
        # covers every *.trytone.ai subdomain in deployed envs.
        self.CORS_ALLOW_ORIGINS: list = [
            o.strip() for o in get_secret("CORS_ALLOW_ORIGINS").split(",") if o.strip()
        ]
        self.CORS_ALLOW_ORIGIN_REGEX: str = get_secret("CORS_ALLOW_ORIGIN_REGEX")

        self.POD_PINNING_ENABLED: bool = _bool_env(get_secret("POD_PINNING_ENABLED"))
        # Telephony-free WebSocket test endpoint (/ws/test). Runs a real, paid
        # LLM/STT/TTS pipeline and takes no auth, so it is OFF by default and should
        # stay off in production — enable only in dev/staging for agent testing.
        self.ENABLE_WS_TEST_ENDPOINT: bool = _bool_env(get_secret("ENABLE_WS_TEST_ENDPOINT"))
        self.CALL_SERVER_HOST: str = get_secret("CALL_SERVER_HOST")
        self.CALL_WORKER_PREFIX: str = get_secret("CALL_WORKER_PREFIX")
        self.POD_SYNC_NAMESPACE: str = get_secret("POD_SYNC_NAMESPACE")
        # Dedicated OUTBOUND voice-pod pool (WebSocket "test bridge" trigger runs its media here,
        # NOT on the API/orchestrator pod — see WebSocketCallEngine). The originator picks a pod
        # from this StatefulSet (via PodPicker over this prefix) and hands the bridge off over the
        # StatefulSet's headless service (intra-cluster, no ingress) at ``{pod}.{headless}.{ns}.svc``.
        self.OUTBOUND_CALL_WORKER_PREFIX: str = get_secret("OUTBOUND_CALL_WORKER_PREFIX")
        self.OUTBOUND_CALL_HEADLESS_SERVICE: str = get_secret("OUTBOUND_CALL_HEADLESS_SERVICE")
        self.OUTBOUND_CALL_WORKER_PORT: int = _int_env(get_secret("OUTBOUND_CALL_WORKER_PORT"))
        # Per voice-pod concurrent-call ceiling, enforced at the pod's ws-bridge-start route
        # (429 when full → the originator queues the overflow). 0/<=0 = unlimited. Set on the
        # call-worker manifests; previously an unread env var, now honoured in code.
        self.MAX_CONCURRENT_CALLS: int = _int_env(get_secret("MAX_CONCURRENT_CALLS"))
        # Optional shared secret for the intra-cluster ws-bridge-start hand-off. Empty = no check
        # (same trust model as /ws — the route is not exposed via any ingress). When set, the
        # originator sends it and the pod requires it.
        self.WS_BRIDGE_INTERNAL_TOKEN: str = get_secret("WS_BRIDGE_INTERNAL_TOKEN")

        # Public base URL (scheme + host, no /api/v1) that Twilio can reach for
        # outbound-call TwiML + status callbacks. Root-mounted telephony routes hang
        # off this (e.g. {BASE_CALL_URL}/twiml/outbound). Required for outbound dialing;
        # scheduled dials run in the worker with no request context to derive it from.
        # Locally: an ngrok URL. Prod: the public API host.
        self.BASE_CALL_URL: str = get_secret("BASE_CALL_URL").rstrip("/")

        # WebSocket call trigger (provider="websocket"): the outbound call is bridged over a
        # WebSocket client to a REMOTE deployment's /ws/test endpoint (agent-to-agent, no PSTN),
        # instead of Twilio placing a phone call. WS_CALL_TARGET_URL is that remote's base
        # (scheme + host, e.g. wss://staging-test.trytone.ai) — required; empty disables the WS
        # trigger. The remote agent is normally resolved by the dialed to_number on that side
        # (like a real call); WS_CALL_TARGET_AGENT_ID is an OPTIONAL fallback used only when a
        # call carries no number to route on.
        self.WS_CALL_TARGET_URL: str = get_secret("WS_CALL_TARGET_URL").rstrip("/")
        self.WS_CALL_TARGET_AGENT_ID: str = get_secret("WS_CALL_TARGET_AGENT_ID")
        # Single-process / local-dev escape hatch. The WS bridge is normally handed off to a
        # dedicated outbound-call-worker pod (keeps media OFF the API/orchestrator pod). When no such
        # pod is registered — e.g. a local `uvicorn main:app` with no WORKER_MODE=voice sibling —
        # PodPicker.for_outbound finds nothing and the row would hold forever. With this flag ON the
        # originator runs the bridge IN-PROCESS instead. OFF by default so staging/prod keep the pod
        # hand-off; set true only for local/single-node runs.
        self.WS_BRIDGE_ALLOW_INLINE: bool = _bool_env(get_secret("WS_BRIDGE_ALLOW_INLINE"))
        # NB: access to the WebSocket ("test bridge") trigger is limited to users whose
        # ``members.role == 'super_admin'`` — see OutboundCallService.is_ws_trigger_allowed. The
        # role is assigned via SQL only (no UI/API), so the allowlist changes without a redeploy.

        self.APPLICATION_URL: str = get_secret("APPLICATION_URL")
        self.RESEND_API_KEY: str = get_secret("RESEND_API_KEY")

        self.LICENSE_KEY: Optional[str] = get_secret("TONE_LICENSE_KEY") or None
        self.SKIP_LICENSE_CHECK: bool = _bool_env(get_secret("SKIP_LICENSE_CHECK"))

        self.DEFAULT_ORG_ID: str = get_secret("DEFAULT_ORG_ID")

        # Auth token for scripts/API calls
        self.AUTH_TOKEN: str = get_secret("AUTH_TOKEN")

        # Base API URL for scripts
        self.BASE_API_URL: str = get_secret("BASE_API_URL")

        # Redis
        self.REDIS_URL: str = get_secret("REDIS_URL")

        # Logging. LOG_LEVEL is the baseline level every process boots at. For calls,
        # a finer level can be set per organization / per agent in the DB
        # (agents.log_level > organizations.log_level > this env baseline) — resolved by
        # core/services/log_level_resolver.py. Blank/invalid falls back to INFO.
        self.LOG_LEVEL: str = get_secret("LOG_LEVEL")

        # Cloudflare R2 storage
        self.R2_ACCESS_KEY_ID: str = get_secret("R2_ACCESS_KEY_ID")
        self.R2_SECRET_ACCESS_KEY: str = get_secret("R2_SECRET_ACCESS_KEY")
        self.R2_BUCKET_NAME: str = get_secret("R2_BUCKET_NAME")
        self.R2_ENDPOINT_URL: str = get_secret("R2_ENDPOINT_URL")

        # Google OAuth
        self.GOOGLE_CLIENT_ID: str = get_secret("GOOGLE_CLIENT_ID")
        self.GOOGLE_CLIENT_SECRET: str = get_secret("GOOGLE_CLIENT_SECRET")

        # Pre-registered OAuth clients for MCP servers that don't support Dynamic Client
        # Registration (RFC 7591). HubSpot's official MCP server (mcp.hubspot.com) requires
        # creating an "MCP Auth App" in the HubSpot developer portal to obtain these.
        self.HUBSPOT_MCP_CLIENT_ID: str = get_secret("HUBSPOT_MCP_CLIENT_ID")
        self.HUBSPOT_MCP_CLIENT_SECRET: str = get_secret("HUBSPOT_MCP_CLIENT_SECRET")

        self.SALESFORCE_CLIENT_ID: str = get_secret("SALESFORCE_CLIENT_ID")
        self.SALESFORCE_CLIENT_SECRET: str = get_secret("SALESFORCE_CLIENT_SECRET")
        self.SALESFORCE_MY_DOMAIN: str = get_secret("SALESFORCE_MY_DOMAIN")

        self.LLAMA_CLOUD_API_KEY: str = get_secret("LLAMA_CLOUD_API_KEY")

        # Global OpenAI key used as a fallback for AI helper features (e.g. system-prompt
        # generation) when an org hasn't configured its own provider key.
        self.OPENAI_API_KEY: str = get_secret("OPENAI_API_KEY")

        self.LIVEKIT_URL: str = get_secret("LIVEKIT_URL")
        self.LIVEKIT_API_KEY: str = get_secret("LIVEKIT_API_KEY")
        self.LIVEKIT_API_SECRET: str = get_secret("LIVEKIT_API_SECRET")
        self.DAILY_API_KEY: str = get_secret("DAILY_API_KEY")
        self.WEBRTC_CLIENT_BASE_URL: str = get_secret("WEBRTC_CLIENT_BASE_URL")
        self.CALL_WORKER_INTERNAL_URL: str = get_secret("CALL_WORKER_INTERNAL_URL")

        self.SEND_SMS_DEFAULT_TO_NUMBER: str = get_secret("SEND_SMS_DEFAULT_TO_NUMBER")

        # ── Grafana Loki (log egress + per-call read-back) ──────────────────
        # LOKI_URL/LOKI_USER/GRAFANA_API_KEY are the same secrets the Alloy
        # DaemonSet uses to PUSH logs to Grafana Cloud (see the monitoring
        # manifests). We surface them here so the per-call log sync can READ a
        # finished call's lines back out of Loki. All blank in local dev, which
        # makes loki_read_configured() False and the sync a safe no-op.
        self.LOKI_URL: str = get_secret("LOKI_URL")  # push endpoint (…/loki/api/v1/push)
        self.LOKI_USER: str = get_secret("LOKI_USER")
        self.GRAFANA_API_KEY: str = get_secret("GRAFANA_API_KEY")

        # Query endpoint for reading logs back. Derived from the push URL
        # (swap the trailing /push for /query_range) when LOKI_QUERY_URL is not
        # explicitly provided.
        self.LOKI_QUERY_URL: str = (
            get_secret("LOKI_QUERY_URL")
            or (self.LOKI_URL.replace("/loki/api/v1/push", "/loki/api/v1/query_range") if self.LOKI_URL else "")
        )
        # Read creds default to the push creds; override if a dedicated
        # read-scoped (logs:read) token is provisioned.
        self.LOKI_QUERY_USER: str = get_secret("LOKI_QUERY_USER") or self.LOKI_USER
        self.LOKI_QUERY_TOKEN: str = get_secret("LOKI_QUERY_TOKEN") or self.GRAFANA_API_KEY

        # Per-call sync tuning. No enable/disable flag — the post-call action is
        # always wired; loki_read_configured() alone gates it.
        # Loki stream selector for the per-call log fetch — the trace_id line
        # filter does the real per-call scoping; this just narrows the streams.
        # Set LOKI_SYNC_APP_LABEL to a single workload (builds {app="<value>"}),
        # e.g. staging-tone-call-worker. Left blank, the query falls back to the
        # env-agnostic {component=~"call|api"} (Alloy labels tone pods with
        # component={call,api,worker}).
        self.LOKI_SYNC_APP_LABEL: str = get_secret("LOKI_SYNC_APP_LABEL").strip()
        self.LOKI_SYNC_DELAY_SECONDS: int = _int_env(get_secret("LOKI_SYNC_DELAY_SECONDS"))
        self.LOKI_SYNC_PRE_BUFFER_SECONDS: int = _int_env(get_secret("LOKI_SYNC_PRE_BUFFER_SECONDS"))
        self.LOKI_SYNC_POST_BUFFER_SECONDS: int = _int_env(get_secret("LOKI_SYNC_POST_BUFFER_SECONDS"))
        self.LOKI_SYNC_PAGE_LIMIT: int = _int_env(get_secret("LOKI_SYNC_PAGE_LIMIT"))
        self.LOKI_SYNC_MAX_PAGES: int = _int_env(get_secret("LOKI_SYNC_MAX_PAGES"))
        self.LOKI_SYNC_HTTP_TIMEOUT: int = _int_env(get_secret("LOKI_SYNC_HTTP_TIMEOUT"))
        self.LOKI_SYNC_MAX_RETRIES: int = _int_env(get_secret("LOKI_SYNC_MAX_RETRIES"))

        # Per-batch outbound concurrency knob — the UI "Concurrent calls" selector's upper
        # bound AND the default limit a batch gets when it doesn't request one. NOT a global
        # in-flight ceiling: the limit is enforced per scheduling batch (rows sharing a
        # ``batch_id``), so N concurrent batches can each run up to this many at once. 0
        # = unset: the selector has no cap and a batch with no requested value runs
        # with no per-batch limit. See core/services/outbound_capacity.py for the resolver.
        self.MAX_CONCURRENT_OUTBOUND_CALLS: int = _int_env(get_secret("MAX_CONCURRENT_OUTBOUND_CALLS"))
        # Cap for the OUTBOUND best-effort background thread pools — pipeline cache pre-warming
        # (after a dial, while it rings) and the completion refill (enqueueing a batch's next
        # call off the status webhook). 0 = ON-DEMAND: no threads are held idle; one
        # is created at call time only when needed, up to the runtime's default cap. Set > 0 to
        # pin an explicit ceiling. Kept as a knob for future tuning.
        self.OUTBOUND_BG_WORKERS: int = _int_env(get_secret("OUTBOUND_BG_WORKERS"))

        # ── RAG ingestion defaults ──────────────────────────────────────────
        # Baseline parser / tokeniser / embedder / vector-store used when a
        # caller doesn't supply an override. Every value maps to a registry
        # entry (see core/services/rag/parser_factory.py, tokeniser_factory.py,
        # embedder_factory.py, factory.py). Consumed only by
        # IngestionRunService.resolve_run_config — no other file bakes these in.
        self.DEFAULT_PARSER: str = get_secret("DEFAULT_PARSER")
        self.DEFAULT_TOKENISER: str = get_secret("DEFAULT_TOKENISER")
        self.DEFAULT_EMBEDDING_PROVIDER: str = get_secret("DEFAULT_EMBEDDING_PROVIDER")
        self.DEFAULT_EMBEDDING_MODEL: str = get_secret("DEFAULT_EMBEDDING_MODEL")
        self.DEFAULT_EMBEDDING_DIMENSIONS: int = _int_env(get_secret("DEFAULT_EMBEDDING_DIMENSIONS"))
        self.DEFAULT_VECTOR_STORE: str = get_secret("DEFAULT_VECTOR_STORE")

        # Pinecone vector store — API key for the "pinecone" backend in the RAG
        # store factory. Empty in envs that only use pgvector; the store itself
        # raises EmbeddingProviderUnavailableError if a run requests pinecone
        # without a key configured.
        self.PINECONE_API_KEY: str = get_secret("PINECONE_API_KEY")

        # ── RAG evaluation harness ──────────────────────────────────────────
        # Auto-runs after every successful ingestion (IngestionRunService.complete_run
        # enqueues eval_ingestion_run when EVAL_AUTO_RUN_ENABLED is true). All
        # eval knobs live here — no other file bakes them in.
        self.EVAL_AUTO_RUN_ENABLED: bool = _bool_env(get_secret("EVAL_AUTO_RUN_ENABLED"))
        self.EVAL_GENERATION_MODEL: str = get_secret("EVAL_GENERATION_MODEL")
        self.EVAL_ANSWER_MODEL: str = get_secret("EVAL_ANSWER_MODEL")
        self.EVAL_JUDGE_MODEL: str = get_secret("EVAL_JUDGE_MODEL")
        self.EVAL_TOP_K: int = _int_env(get_secret("EVAL_TOP_K"))
        self.EVAL_MAX_CONTEXT_CHARS: int = _int_env(get_secret("EVAL_MAX_CONTEXT_CHARS"))
        # EVAL_JUDGE_ENGINE — "deepeval" (production) | "legacy" (custom
        # LLM-as-judge fallback). Selection is done once in
        # judge_factory.build_judge_service; no other file inspects this value.
        self.EVAL_JUDGE_ENGINE: str = get_secret("EVAL_JUDGE_ENGINE")
        # EVAL_METRIC_THRESHOLD — score at or above which one DeepEval metric
        # is PASS. Used to derive the aggregate PASS/PARTIAL/FAIL verdict from
        # per-metric scores. 0.7 is DeepEval's own default. No fallback: the
        # key is in MANDATORY_KEYS so an empty value already aborts startup,
        # and range-validity is enforced at judge build time in
        # ``metric_registry.build_metrics`` (must be in (0.0, 1.0]).
        _raw_threshold = get_secret("EVAL_METRIC_THRESHOLD")
        self.EVAL_METRIC_THRESHOLD: float = float(_raw_threshold) if _raw_threshold else 0.0
        # EVAL_METRICS_ENABLED — comma-separated DeepEval metric names to run
        # per question. Every name must be registered in
        # metric_registry.SUPPORTED_METRICS or the judge raises
        # EvalConfigurationError on first use.
        self.EVAL_METRICS_ENABLED: list[str] = [
            m.strip()
            for m in (get_secret("EVAL_METRICS_ENABLED") or "").split(",")
            if m.strip()
        ]

        # ── Agent LLM eval harness ──────────────────────────────────────────
        # AGENT_LLM_EVAL_METRICS_ENABLED — comma-separated DeepEval metric
        # names run per scenario by ``evals/agent_llm_eval.py`` /
        # ``AgentLlmEvalService``. Every name must be registered in
        # ``metric_registry.SUPPORTED_METRICS``; individual scenarios may
        # override this list via ``LLMScenario.metrics``.
        self.AGENT_LLM_EVAL_METRICS_ENABLED: list[str] = [
            m.strip()
            for m in (get_secret("AGENT_LLM_EVAL_METRICS_ENABLED") or "").split(",")
            if m.strip()
        ]
        # AGENT_LLM_EVAL_JUDGE_MODEL / _METRIC_THRESHOLD / _AUTO_RUN_ENABLED —
        # optional per-flavor overrides read by
        # ``core.services.org_settings.get_agent_llm_eval_settings`` when the
        # org's ``eval_settings.llm_evals.*`` JSONB doesn't override them.
        # NOT in ``MANDATORY_KEYS`` — the resolver falls through to a
        # hardcoded default if the env is unset, so existing deployments boot
        # unchanged. Ops can set these per-env to override the shipped default
        # without touching per-org DB rows.
        self.AGENT_LLM_EVAL_JUDGE_MODEL: str = get_secret("AGENT_LLM_EVAL_JUDGE_MODEL")
        # Non-mandatory numeric env — a fat-fingered value must not crash
        # every process at import. Log a critical warning and fall back to
        # 0.0 (the resolver treats that as unset and drops to the hardcoded
        # default, matching the "env not set" behavior).
        _raw_agent_llm_threshold = get_secret("AGENT_LLM_EVAL_METRIC_THRESHOLD")
        if _raw_agent_llm_threshold:
            try:
                self.AGENT_LLM_EVAL_METRIC_THRESHOLD: float = float(
                    _raw_agent_llm_threshold
                )
            except ValueError:
                logger.critical(
                    "AGENT_LLM_EVAL_METRIC_THRESHOLD is not a number: {!r} — "
                    "falling back to org / hardcoded default (0.7)",
                    _raw_agent_llm_threshold,
                )
                self.AGENT_LLM_EVAL_METRIC_THRESHOLD = 0.0
        else:
            self.AGENT_LLM_EVAL_METRIC_THRESHOLD = 0.0
        self.AGENT_LLM_EVAL_AUTO_RUN_ENABLED: bool = _bool_env(
            get_secret("AGENT_LLM_EVAL_AUTO_RUN_ENABLED")
        )

        # Fail-fast if any mandatory env var is missing. Runs LAST so every
        # field is populated before we inspect it. Aborts process on failure.
        self._validate_required()

    def _validate_required(self) -> None:
        """Abort process startup when mandatory env vars are missing.

        Runs once per ``Settings()`` instantiation (i.e. on first import of
        ``shared.config``) so every entry point — API pod, EE pod, ingestion
        worker, seed scripts — enforces the same contract.

        Tier A (``MANDATORY_KEYS``) is enforced in every env; Tier B
        (``MANDATORY_PROD_KEYS``) is added when ``ENV`` is not one of
        ``DEV_ENV_NAMES``. Values matching ``INSECURE_PLACEHOLDERS`` are
        treated as unset.

        Detection uses the RAW value tracked in ``self._raw`` (or the OS env
        for bootstrap keys like INFISICAL_TOKEN that are not stored on the
        Settings instance), NOT the coerced attribute — so an int knob whose
        legitimate value is 0 doesn't get flagged as missing.

        On failure: emit a single ``logger.critical`` line naming every
        missing key (loguru → stderr → Alloy DaemonSet → Loki → Grafana),
        then ``sys.exit(1)`` via ``SystemExit``. K8s marks the pod
        CrashLoopBackOff and Grafana surfaces the CRITICAL line.
        """
        env_name = (os.getenv("ENV") or self.ENVIRONMENT or "").lower()
        is_deployed = bool(env_name) and env_name not in DEV_ENV_NAMES

        required: list[str] = list(MANDATORY_KEYS)
        if is_deployed:
            required.extend(MANDATORY_PROD_KEYS)

        missing: list[str] = []
        for key in required:
            raw = self._raw.get(key, "") or os.environ.get(key, "") or ""
            insecure = INSECURE_PLACEHOLDERS.get(key, set())
            if not raw or raw in insecure:
                missing.append(key)

        if not missing:
            return

        keys_block = "\n".join(f"  - {k}" for k in missing)
        logger.critical(
            "[config] Pod startup aborted — missing {count} required env "
            "variable(s) for ENV={env}:\n{keys}\nSee .env.example for the "
            "full template and required set.",
            count=len(missing),
            env=env_name or "<unset>",
            keys=keys_block,
        )
        raise SystemExit(1)

    def loki_read_configured(self) -> bool:
        """True only when we have enough to read a call's logs back from Loki.

        The single guard for the whole feature: when False (e.g. local dev with
        no Loki secrets), the post-call action, worker job and manual endpoint
        all no-op instead of erroring."""
        return bool(self.LOKI_QUERY_URL and self.LOKI_QUERY_TOKEN)


# Lazy module-level singleton. Construction (and therefore validation) fires
# on first attribute access via PEP 562 __getattr__, not on module import.
# Real callers do ``from shared.config import settings`` which triggers the
# getattr immediately and preserves fail-fast semantics. Tests instantiate
# ``config.Settings()`` directly (bypassing this singleton) so they can drive
# the validator with a monkeypatched env instead of the process env.
_settings: "Settings | None" = None


def __getattr__(name: str):
    global _settings
    if name == "settings":
        if _settings is None:
            _settings = Settings()
        return _settings
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
