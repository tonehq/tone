import sys
import os
from uuid import uuid4

from core.logging import setup_logging
setup_logging()

from loguru import logger

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pipecat.runner.types import (LiveKitRunnerArguments,
                                  WebSocketRunnerArguments)

from core.bot import bot
from core.services.webrtc.dispatcher import get_bot_dispatcher
from shared.config import settings
from core.internal.machine import generate_fingerprint
from core.internal.license import init_license_validator, get_license_info
from core.internal.capabilities import init_capabilities, is_ee_enabled, get_capabilities

# Call pods (WORKER_MODE=voice) only serve /ws, /twiml, /health, /ready,
# /metrics, /status, /environment, and pod-pinned WebRTC signaling. All CRUD
# routers (auth, users, orgs, agents, tools, dashboard, ...) plus knowledge
# base are handled by API pods, never call pods. Skipping their imports here
# avoids pulling docling + HuggingFace transformers + Pydantic schemas + a
# large SQLAlchemy graph, shaving several seconds off container startup.
_WORKER_MODE = os.environ.get("WORKER_MODE", "").lower()
_LOAD_FULL_API = _WORKER_MODE != "voice"

# webrtc router is always loaded — call pods receive
#   POST /api/v1/webrtc/agent/{id}/start   (via /pod/{N}/... pod-pinning)
from core.api.v1 import sip_trunks, webrtc

if _LOAD_FULL_API:
    from core.api.v1 import (
        auth, users, organizations, agent_configs, channels, oauth,
        agents, agent_readiness, agent_llm_evals, agent_profile_variables,
        benchmarks, mcp_servers, services, tools, dashboard,
        call_logs, call_metrics, call_transcript_evals, sessions, workflows, audit_logs,
        app_integrations, outbound_calls, admin, contacts,
        contact_directories, contact_datasources, contact_schemas,
        contact_syncs, agent_contacts,
        ingestion_configs,
        generated_api_keys,
    )
from core.middleware.request_context import RequestContextMiddleware
from core.api.telephony_routes import router as telephony_router
from core.api.sip_routes import router as sip_router
from core.api.monitoring_routes import (
    router as monitoring_router,
    active_calls_inc,
    active_calls_dec,
    active_calls_count,
    set_draining,
    is_draining,
)
import core.models

skip_license = settings.SKIP_LICENSE_CHECK

fingerprint = generate_fingerprint(settings.DATABASE_URL)
init_license_validator(settings.LICENSE_KEY, skip_license_check=skip_license)
license_info = get_license_info(fingerprint)
capabilities = init_capabilities(fingerprint, skip_license_check=skip_license)

from core.internal.license import LicenseTier

ee_folder_exists = os.path.isdir(os.path.join(os.path.dirname(__file__), "ee"))

if not skip_license:
    if ee_folder_exists and license_info.tier == LicenseTier.FREE:
        print("ERROR: EE code detected but no valid EE license found.")
        print("Please provide a valid TONE_LICENSE_KEY or remove the 'ee' folder to run Core edition.")
        sys.exit(1)

    if not license_info.is_valid and settings.LICENSE_KEY:
        print(f"License validation failed: {license_info.validation_error}")
        if license_info.validation_error == "fingerprint_mismatch":
            print("License is bound to a different instance.")
            sys.exit(1)
else:
    print("License check skipped (SKIP_LICENSE_CHECK=true)")

ee_enabled = is_ee_enabled()
edition = "enterprise" if ee_enabled else "core"

app = FastAPI(title=f"Tone API - {edition.title()}", version="1.0.0")

# Cookie-based auth means requests are credentialed, and browsers reject
# `Allow-Origin: *` with credentials — so we reflect an explicit allow-list
# (exact origins for local dev + a regex for every *.trytone.ai subdomain).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization", "tenant_id", "Content-Type"],
)
app.add_middleware(RequestContextMiddleware)

api_v1 = FastAPI()

api_v1.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization", "tenant_id", "Content-Type"],
)
# RequestContextMiddleware is registered on the outer ``app`` only — the
# api_v1 sub-app is mounted under it, so the outer middleware already wraps
# every /api/v1/* request. Adding it here would double-set the context.


# ── Readiness service errors → HTTP ──────────────────────────────────────────
# ``ReadinessService`` is transport-agnostic (raises typed errors from
# ``core.services.readiness.errors``, never ``HTTPException``) so it can be
# reused from a CLI / job / other service. This one handler on the api_v1
# sub-app maps that error family to the SAME HTTP responses the routes returned
# before, for every readiness + publish-gate route across both editions — so no
# per-route try/except is needed. Registered on ``api_v1`` (not the outer app)
# because mounted sub-apps resolve their own exception handlers.
from fastapi.encoders import jsonable_encoder  # noqa: E402

from core.services.readiness.errors import (  # noqa: E402
    AgentNotFoundError,
    InvalidAgentIdError,
    PublishGateError,
    ReadinessError,
    ReadinessRateLimitedError,
    ReadinessRunNotFoundError,
)

_READINESS_ERROR_STATUS = {
    InvalidAgentIdError: 400,
    AgentNotFoundError: 404,
    ReadinessRateLimitedError: 429,
    ReadinessRunNotFoundError: 404,
}


async def _readiness_error_handler(_request: Request, exc: ReadinessError) -> JSONResponse:
    """Map a readiness service error onto the HTTP response its route used to
    raise directly, keeping the wire contract byte-for-byte identical."""
    if isinstance(exc, PublishGateError):
        # Structured body the publish flow switches on (reason + full report).
        return JSONResponse(
            status_code=400,
            content=jsonable_encoder(
                {
                    "detail": {
                        "reason": exc.reason,
                        "message": exc.message,
                        "report": exc.report.model_dump(),
                    }
                }
            ),
        )
    # Exact-type lookup; any future subclass falls back to 400 rather than 500.
    status_code = _READINESS_ERROR_STATUS.get(type(exc), 400)
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({"detail": str(exc)}),
    )


api_v1.add_exception_handler(ReadinessError, _readiness_error_handler)


if ee_enabled:
    # EE routers are imported individually because ``ee/api/v1/__init__.py``
    # no longer eagerly imports siblings (some still reference dropped
    # pre-v2 models). CRUD routers are skipped on call pods (see _LOAD_FULL_API).
    if _LOAD_FULL_API:
        from ee.api.v1 import auth as ee_auth
        from ee.api.v1 import users as ee_users
        from ee.api.v1 import organizations as ee_organizations
        from ee.api.v1 import agent_configs as ee_agent_configs
        from ee.api.v1 import channels as ee_channels
        from ee.api.v1 import oauth as ee_oauth
        from ee.api.v1 import agents as ee_agents
        from ee.api.v1 import agent_readiness as ee_agent_readiness
        from ee.api.v1 import mcp_servers as ee_mcp_servers
        from ee.api.v1 import app_integrations as ee_app_integrations
        from ee.api.v1 import services as ee_services
        from ee.api.v1 import tools as ee_tools
        from ee.api.v1 import dashboard as ee_dashboard
        from ee.api.v1 import call_logs as ee_call_logs
        from ee.api.v1 import call_metrics as ee_call_metrics
        from ee.api.v1 import generated_api_keys as ee_generated_api_keys

        api_v1.include_router(ee_auth.router, prefix="/auth", tags=["auth"])
        api_v1.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
        api_v1.include_router(ee_users.router, prefix="/user", tags=["users"])
        api_v1.include_router(ee_organizations.router, prefix="/organization", tags=["organization"])
        api_v1.include_router(ee_agent_configs.router, prefix="/agent_config", tags=["agent_config"])
        api_v1.include_router(ee_channels.router, prefix="/channel", tags=["channel"])
        api_v1.include_router(sip_trunks.router, prefix="/sip-trunk", tags=["sip-trunk"])
        api_v1.include_router(ee_oauth.router, prefix="/oauth", tags=["oauth"])
        from ee.api.v1 import knowledge_base as ee_knowledge_base
        api_v1.include_router(ee_knowledge_base.router, prefix="/knowledge-base", tags=["knowledge-base"])
        api_v1.include_router(ee_agents.router, prefix="/agent", tags=["agent"])
        api_v1.include_router(ee_agent_readiness.router, prefix="/agent", tags=["agent-readiness"])
        # Agent LLM (Level-2) evals — no EE variant; router paths include the
        # /agents/{agent_id}/llm-evals prefix so no include_router prefix is set.
        api_v1.include_router(agent_llm_evals.router, tags=["agent-llm-evals"])
        # Agent Profile Variables — per-agent {{profile.<key>}} placeholders.
        # Router paths carry the /agents/{agent_id}/profile-variables prefix.
        api_v1.include_router(
            agent_profile_variables.router, tags=["agent-profile-variables"]
        )
        # Post-call transcript (Level-3) evals — read-only in v1. Router
        # paths include /calls/{call_id}/eval-results so no prefix.
        api_v1.include_router(
            call_transcript_evals.router, tags=["call-transcript-evals"],
        )
        api_v1.include_router(benchmarks.router, prefix="/agent", tags=["benchmarks"])
        api_v1.include_router(ee_mcp_servers.router, prefix="/mcp-server", tags=["mcp-server"])
        api_v1.include_router(ee_app_integrations.router, prefix="/app-integration", tags=["app-integration"])
        api_v1.include_router(ee_services.router, prefix="/services", tags=["services"])
        api_v1.include_router(ee_tools.router, prefix="/tool", tags=["tool"])
        api_v1.include_router(ee_dashboard.router, prefix="/dashboard", tags=["dashboard"])
        api_v1.include_router(ee_call_logs.router, prefix="/call-log", tags=["call-log"])
        api_v1.include_router(ee_call_metrics.router, prefix="/call-metrics", tags=["call-metrics"])
        api_v1.include_router(workflows.router, prefix="/workflow", tags=["workflow"])
        api_v1.include_router(audit_logs.router, prefix="/audit-log", tags=["audit-log"])
        api_v1.include_router(outbound_calls.router, prefix="/outbound-call", tags=["outbound-call"])
        # Contact Directories module: contacts.router carries full paths
        # (/contact-directories/{id}/contacts/*, /contacts/{id}, /contact/schedule-calls)
        # so it mounts at the api-v1 root; the resource routers set their own prefixes.
        api_v1.include_router(contacts.router, tags=["contact"])
        api_v1.include_router(contact_directories.router, prefix="/contact-directories", tags=["contact-directory"])
        api_v1.include_router(contact_datasources.router, prefix="/contact-datasources", tags=["contact-datasource"])
        api_v1.include_router(contact_schemas.router, tags=["contact-schema"])
        api_v1.include_router(contact_schemas.field_router, tags=["contact-schema"])
        api_v1.include_router(contact_syncs.router, prefix="/contact-syncs", tags=["contact-sync"])
        api_v1.include_router(agent_contacts.router, prefix="/agents", tags=["agent-contacts"])
        api_v1.include_router(ingestion_configs.router, tags=["ingestion-config"])
        api_v1.include_router(admin.router, prefix="/admin", tags=["admin"])
        api_v1.include_router(
            ee_generated_api_keys.router,
            prefix="/generated-api-keys",
            tags=["generated-api-keys"],
        )
    # webrtc is always mounted — needed on call pods for WebRTC signaling.
    api_v1.include_router(webrtc.router, prefix="/webrtc", tags=["webrtc"])
    print("EE edition: auth-schema routes loaded (other routers temporarily disabled pending v2 schema migration)")
else:
    if _LOAD_FULL_API:
        from core.api.v1 import knowledge_base
        api_v1.include_router(auth.router, prefix="/auth", tags=["auth"])
        api_v1.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
        api_v1.include_router(users.router, prefix="/user", tags=["users"])
        api_v1.include_router(organizations.router, prefix="/organization", tags=["organization"])
        api_v1.include_router(agent_configs.router, prefix="/agent_config", tags=["agent_config"])
        api_v1.include_router(channels.router, prefix="/channel", tags=["channel"])
        api_v1.include_router(sip_trunks.router, prefix="/sip-trunk", tags=["sip-trunk"])
        api_v1.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
        api_v1.include_router(knowledge_base.router, prefix="/knowledge-base", tags=["knowledge-base"])
        api_v1.include_router(agents.router, prefix="/agent", tags=["agent"])
        api_v1.include_router(agent_readiness.router, prefix="/agent", tags=["agent-readiness"])
        # Agent LLM (Level-2) evals — router paths already include the
        # /agents/{agent_id}/llm-evals prefix so no include_router prefix.
        api_v1.include_router(agent_llm_evals.router, tags=["agent-llm-evals"])
        # Agent Profile Variables — per-agent {{profile.<key>}} placeholders.
        # Router paths carry the /agents/{agent_id}/profile-variables prefix.
        api_v1.include_router(
            agent_profile_variables.router, tags=["agent-profile-variables"]
        )
        # Post-call transcript (Level-3) evals — read-only in v1. Router
        # paths include /calls/{call_id}/eval-results so no prefix.
        api_v1.include_router(
            call_transcript_evals.router, tags=["call-transcript-evals"],
        )
        api_v1.include_router(benchmarks.router, prefix="/agent", tags=["benchmarks"])
        api_v1.include_router(mcp_servers.router, prefix="/mcp-server", tags=["mcp-server"])
        api_v1.include_router(app_integrations.router, prefix="/app-integration", tags=["app-integration"])
        api_v1.include_router(services.router, prefix="/services", tags=["services"])
        api_v1.include_router(tools.router, prefix="/tool", tags=["tool"])
        api_v1.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
        api_v1.include_router(call_logs.router, prefix="/call-log", tags=["call-log"])
        api_v1.include_router(call_metrics.router, prefix="/call-metrics", tags=["call-metrics"])
        api_v1.include_router(workflows.router, prefix="/workflow", tags=["workflow"])
        api_v1.include_router(audit_logs.router, prefix="/audit-log", tags=["audit-log"])
        api_v1.include_router(outbound_calls.router, prefix="/outbound-call", tags=["outbound-call"])
        # Contact Directories module: contacts.router carries full paths
        # (/contact-directories/{id}/contacts/*, /contacts/{id}, /contact/schedule-calls)
        # so it mounts at the api-v1 root; the resource routers set their own prefixes.
        api_v1.include_router(contacts.router, tags=["contact"])
        api_v1.include_router(contact_directories.router, prefix="/contact-directories", tags=["contact-directory"])
        api_v1.include_router(contact_datasources.router, prefix="/contact-datasources", tags=["contact-datasource"])
        api_v1.include_router(contact_schemas.router, tags=["contact-schema"])
        api_v1.include_router(contact_schemas.field_router, tags=["contact-schema"])
        api_v1.include_router(contact_syncs.router, prefix="/contact-syncs", tags=["contact-sync"])
        api_v1.include_router(agent_contacts.router, prefix="/agents", tags=["agent-contacts"])
        api_v1.include_router(ingestion_configs.router, tags=["ingestion-config"])
        api_v1.include_router(admin.router, prefix="/admin", tags=["admin"])
        api_v1.include_router(
            generated_api_keys.router,
            prefix="/generated-api-keys",
            tags=["generated-api-keys"],
        )
    # webrtc is always mounted — needed on call pods for WebRTC signaling.
    api_v1.include_router(webrtc.router, prefix="/webrtc", tags=["webrtc"])
    print("Core edition: auth-schema routes loaded (other routers temporarily disabled pending v2 schema migration)")


@api_v1.get("/capabilities", tags=["system"])
def get_capabilities_endpoint():
    return {"capabilities": get_capabilities(), "edition": edition, "ee_enabled": ee_enabled}


app.mount("/api/v1", api_v1)

# Telephony router temporarily disabled — depends on AgentChannel/CallLog
# models that were dropped in the v2 schema revamp.


@app.on_event("startup")
def warm_db_pool():
    """Warm up the DB connection pool at server start so the first request is fast."""
    from sqlalchemy import text
    from core.database.session import get_db_context
    try:
        with get_db_context() as db:
            db.execute(text("SELECT 1"))
        print("DB connection pool warmed up")
    except Exception as e:
        print(f"Warning: Failed to warm DB pool: {e}")


@app.on_event("startup")
def init_redis_pool():
    """Initialize Redis connection at server start."""
    from core.services.redis_service import init_redis
    init_redis(settings.REDIS_URL)


@app.on_event("startup")
def warm_up_pipeline_services():
    from core.services.service_warmup import warm_up_services
    warm_up_services()


@app.on_event("startup")
async def warm_worker_pool_startup():
    """Pre-spawn bot worker subprocesses so the first call starts instantly."""
    use_subprocess = os.environ.get("USE_SUBPROCESS_BOT", "false").lower() == "true"
    use_warm_pool = os.environ.get("USE_WARM_POOL", "false").lower() == "true"
    if use_subprocess and use_warm_pool:
        pool_size = int(os.environ.get("WARM_POOL_SIZE", "2"))
        from core.services.warm_worker_pool import WarmWorkerPool
        pool = WarmWorkerPool.get_instance(pool_size=pool_size)
        await pool.start()
    else:
        print("Warm worker pool disabled (set USE_SUBPROCESS_BOT=true and USE_WARM_POOL=true to enable)")


@app.on_event("shutdown")
async def drain_active_calls_shutdown():
    if _WORKER_MODE != "voice":
        return
    import asyncio
    set_draining(True)
    deadline = float(os.environ.get("CALL_DRAIN_TIMEOUT_SECONDS", "1800"))
    waited = 0.0
    step = 5.0
    while active_calls_count() > 0 and waited < deadline:
        logger.info("[shutdown] draining: {} active call(s), waited {:.0f}s", active_calls_count(), waited)
        await asyncio.sleep(step)
        waited += step
    remaining = active_calls_count()
    if remaining:
        logger.warning("[shutdown] drain deadline hit with {} call(s) still active", remaining)
    else:
        logger.info("[shutdown] all calls drained after {:.0f}s", waited)


@app.on_event("shutdown")
async def warm_worker_pool_shutdown():
    try:
        from core.services.warm_worker_pool import WarmWorkerPool
        pool = WarmWorkerPool.get_instance()
        await pool.shutdown()
    except Exception:
        pass


@app.get("/")
def root():
    return {
        "message": f"Tone API - {edition.title()} Edition",
        "version": "1.0.0",
        "edition": edition,
    }


@app.get("/health")
def health():
    return {"status": "ok", "edition": edition, "deployed": True, "version": 2}


@app.get("/ready")
def ready():
    if is_draining():
        return JSONResponse({"ready": False, "draining": True}, status_code=503)
    return {"ready": True}


@app.get("/environment")
def environment():
    return {"environment": settings.ENVIRONMENT}


app.include_router(telephony_router)
app.include_router(sip_router)
app.include_router(monitoring_router)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("[inbound] /ws connection accepted from {}", getattr(websocket.client, "host", "?"))
    body = {
        key: value
        for key in ("agent_id", "direction", "scheduled_call_id")
        if (value := (websocket.query_params.get(key) or "").strip())
    }
    runner_args = WebSocketRunnerArguments(websocket=websocket, body=body)
    try:
        active_calls_inc()
    except Exception:
        logger.debug("[inbound] active_calls_inc failed (metric only)")
    try:
        await bot(runner_args)
    except Exception:
        # The bot's own outer handler already logs the traceback; this is the
        # transport-boundary backstop so a /ws crash is never silent.
        logger.exception("[inbound] /ws bot crashed")
    finally:
        try:
            active_calls_dec()
        except Exception:
            logger.debug("[inbound] active_calls_dec failed (metric only)")
        try:
            await websocket.close()
        except Exception:
            logger.debug("[inbound] /ws close failed")
        logger.info("[inbound] /ws connection closed")


@app.websocket("/ws/test")
async def ws_test_endpoint(websocket: WebSocket) -> None:
    """Telephony-free WebSocket test endpoint — raw PCM in/out, no Twilio.

    Lets a client (``test-cases/pipeline/ws_test_client.py``) drive an agent's pipeline
    directly for testing: connect with ``?agent_id=<uuid>`` or ``?phone_number=<E.164>``,
    stream raw 16-bit PCM, and receive the bot's raw-PCM audio back. It rides the same
    ``bot()`` → ``TelephonyTransport`` path as a real call via the ``"test"`` provider
    (``core/services/transport/test_provider.py``), so the pipeline is identical.

    Gated behind ``ENABLE_WS_TEST_ENDPOINT`` (off in prod): it runs a real, paid
    LLM/STT/TTS pipeline and carries no auth, so it must not be reachable in production.
    """
    if not settings.ENABLE_WS_TEST_ENDPOINT:
        logger.warning("[ws-test] /ws/test rejected — ENABLE_WS_TEST_ENDPOINT is off")
        await websocket.close(code=1008)
        return

    agent_id = (websocket.query_params.get("agent_id") or "").strip()
    phone_number = (websocket.query_params.get("phone_number") or "").strip()
    if not agent_id and not phone_number:
        logger.warning("[ws-test] /ws/test rejected — pass agent_id or phone_number")
        await websocket.close(code=1008)
        return
    try:
        sample_rate = int(websocket.query_params.get("sample_rate") or 16000)
    except (TypeError, ValueError):
        sample_rate = 16000

    await websocket.accept()
    logger.info(
        "[ws-test] /ws/test accepted agent_id={} phone_number={} sample_rate={} from={}",
        agent_id, phone_number, sample_rate, getattr(websocket.client, "host", "?"),
    )

    # Pre-seed call_data + transport_type so TelephonyTransport.build skips the Twilio
    # frame parser (there is no <start> frame on a raw-PCM stream) and resolves the
    # "test" provider directly. agent_id rides in call_data["body"] (promoted by build)
    # and is also set top-level so get_agent_for_call resolves it without the promotion.
    call_data = {
        "from": "",
        "to": phone_number,
        "body": {"agent_id": agent_id} if agent_id else {},
        "stream_id": uuid4().hex,
        "call_id": uuid4().hex,
        "sample_rate": sample_rate,
    }
    body = {"transport_type": "test", "call_data": call_data}
    if agent_id:
        body["agent_id"] = agent_id
    runner_args = WebSocketRunnerArguments(websocket=websocket, body=body)

    try:
        active_calls_inc()
    except Exception:
        logger.debug("[ws-test] active_calls_inc failed (metric only)")
    try:
        await bot(runner_args)
    except Exception:
        logger.exception("[ws-test] /ws/test bot crashed")
    finally:
        try:
            active_calls_dec()
        except Exception:
            logger.debug("[ws-test] active_calls_dec failed (metric only)")
        try:
            await websocket.close()
        except Exception:
            logger.debug("[ws-test] /ws/test close failed")
        logger.info("[ws-test] /ws/test connection closed")


@app.post("/internal/livekit/start")
async def livekit_room_start(request: Request):
    if _WORKER_MODE != "voice":
        logger.warning("[sip] livekit start refused — not a voice pod (WORKER_MODE={!r})", _WORKER_MODE)
        return JSONResponse({"detail": "not a voice pod"}, status_code=404)

    token = settings.WS_BRIDGE_INTERNAL_TOKEN
    if token and request.headers.get("x-ws-bridge-token") != token:
        logger.warning("[sip] livekit start rejected — bad/missing x-ws-bridge-token")
        return JSONResponse({"detail": "forbidden"}, status_code=403)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "invalid JSON body"}, status_code=400)

    room = (body.get("room") or "").strip()
    url = (body.get("url") or "").strip()
    room_token = (body.get("token") or "").strip()
    agent_id = (body.get("agent_id") or "").strip()
    if not room or not url or not room_token or not agent_id:
        return JSONResponse(
            {"detail": "room, url, token and agent_id are required"}, status_code=400
        )

    dispatcher = get_bot_dispatcher()
    if dispatcher.is_active(room):
        return JSONResponse({"room": room, "status": "already_running"}, status_code=200)

    limit = settings.MAX_CONCURRENT_CALLS
    if limit > 0 and dispatcher.active_count() >= limit:
        logger.info("[sip] livekit start at capacity room={} limit={}", room, limit)
        return JSONResponse({"detail": "at capacity"}, status_code=429)

    runner_args = LiveKitRunnerArguments(
        room_name=room,
        url=url,
        token=room_token,
        body={
            "agent_id": agent_id,
            "transport_type": "livekit",
            "direction": body.get("direction") or "inbound",
            "call_data": {
                "from": body.get("from") or "",
                "to": body.get("to") or "",
                "call_id": room,
                "stream_id": room,
                "sip_trunk_id": body.get("trunk_id") or "",
            },
        },
    )
    logger.info("[sip] livekit pipeline starting on voice pod room={} agent={}", room, agent_id)
    await dispatcher.dispatch(room, runner_args)
    return JSONResponse({"room": room, "status": "started"}, status_code=202)


@app.post("/internal/ws-bridge/start")
async def ws_bridge_start(request: Request):
    """Intra-cluster hand-off target: run a WebSocket bridge ON THIS (outbound voice) pod.

    The originator (API/orchestrator pod) picks this pod via ``PodPicker.for_outbound`` and POSTs
    here over the outbound StatefulSet's headless service — so the media pipeline runs here, not on
    the originating pod. Returns 429 when the pod is already at ``MAX_CONCURRENT_CALLS`` so the
    originator queues the row. Cluster-only: not exposed via any ingress; an optional shared
    ``WS_BRIDGE_INTERNAL_TOKEN`` gates it when configured (same trust model as /ws otherwise)."""
    from fastapi.responses import JSONResponse

    from core.services.call_engines.ws_bridge_runner import AtCapacity, start_local_bridge

    # Only voice pods run bridges. If this ever lands on an API/originator pod (WORKER_MODE unset),
    # refuse — running the media here is exactly the OOM this feature exists to prevent.
    if _WORKER_MODE != "voice":
        logger.warning("[ws-bridge] refused — not a voice pod (WORKER_MODE={!r})", _WORKER_MODE)
        return JSONResponse({"detail": "not a voice pod"}, status_code=404)

    token = settings.WS_BRIDGE_INTERNAL_TOKEN
    if token and request.headers.get("x-ws-bridge-token") != token:
        logger.warning("[ws-bridge] rejected — bad/missing x-ws-bridge-token")
        return JSONResponse({"detail": "forbidden"}, status_code=403)

    try:
        body = await request.json()
    except Exception:
        logger.debug("[ws-bridge] rejected — body is not JSON")
        return JSONResponse({"detail": "invalid JSON body"}, status_code=400)

    agent_id = (body.get("agent_id") or "").strip()
    if not agent_id:
        return JSONResponse({"detail": "agent_id is required"}, status_code=400)

    try:
        call_id = start_local_bridge(
            agent_id=agent_id,
            to_number=body.get("to_number") or "",
            from_number=body.get("from_number") or "",
            scheduled_call_id=body.get("scheduled_call_id") or None,
            ws_run_id=body.get("ws_run_id") or None,
            ws_scenario_id=body.get("ws_scenario_id") or None,
        )
    except AtCapacity:
        # Expected under load — the originator turns this into a queued (held) scheduled row.
        logger.info("[ws-bridge] at capacity, refusing bridge (originator will queue)")
        return JSONResponse({"detail": "at capacity"}, status_code=429)
    except ValueError as exc:
        # Misconfiguration (e.g. WS_CALL_TARGET_URL unset) — a client/config error, not 500.
        logger.warning("[ws-bridge] bad request: {}", exc)
        return JSONResponse({"detail": str(exc)}, status_code=400)
    except Exception:
        logger.exception("[ws-bridge] failed to start bridge")
        return JSONResponse({"detail": "bridge start failed"}, status_code=500)

    return {"call_id": call_id, "status": "dialing"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
