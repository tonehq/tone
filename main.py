import sys
import os
from uuid import uuid4

from core.logging import setup_logging
setup_logging()

from loguru import logger

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from pipecat.runner.types import WebSocketRunnerArguments

from core.bot import bot
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
from core.api.v1 import webrtc

if _LOAD_FULL_API:
    from core.api.v1 import (
        auth, users, organizations, agent_configs, channels, oauth,
        agents, agent_readiness, benchmarks, mcp_servers, services, tools, dashboard,
        call_logs, call_metrics, sessions, workflows, audit_logs,
        app_integrations, outbound_calls, admin, contacts,
        contact_directories, contact_datasources, contact_schemas,
        contact_syncs, agent_contacts,
    )
from core.middleware.request_context import RequestContextMiddleware
from core.api.telephony_routes import router as telephony_router
from core.api.monitoring_routes import (
    router as monitoring_router,
    active_calls_inc,
    active_calls_dec,
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

        api_v1.include_router(ee_auth.router, prefix="/auth", tags=["auth"])
        api_v1.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
        api_v1.include_router(ee_users.router, prefix="/user", tags=["users"])
        api_v1.include_router(ee_organizations.router, prefix="/organization", tags=["organization"])
        api_v1.include_router(ee_agent_configs.router, prefix="/agent_config", tags=["agent_config"])
        api_v1.include_router(ee_channels.router, prefix="/channel", tags=["channel"])
        api_v1.include_router(ee_oauth.router, prefix="/oauth", tags=["oauth"])
        from ee.api.v1 import knowledge_base as ee_knowledge_base
        api_v1.include_router(ee_knowledge_base.router, prefix="/knowledge-base", tags=["knowledge-base"])
        api_v1.include_router(ee_agents.router, prefix="/agent", tags=["agent"])
        api_v1.include_router(ee_agent_readiness.router, prefix="/agent", tags=["agent-readiness"])
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
        api_v1.include_router(admin.router, prefix="/admin", tags=["admin"])
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
        api_v1.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
        api_v1.include_router(knowledge_base.router, prefix="/knowledge-base", tags=["knowledge-base"])
        api_v1.include_router(agents.router, prefix="/agent", tags=["agent"])
        api_v1.include_router(agent_readiness.router, prefix="/agent", tags=["agent-readiness"])
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
        api_v1.include_router(admin.router, prefix="/admin", tags=["admin"])
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
async def warm_worker_pool_shutdown():
    """Shut down any idle warm workers on server exit."""
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
    return {"ready": True}


@app.get("/environment")
def environment():
    return {"environment": settings.ENVIRONMENT}


app.include_router(telephony_router)
app.include_router(monitoring_router)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("[inbound] /ws connection accepted from {}", getattr(websocket.client, "host", "?"))
    runner_args = WebSocketRunnerArguments(websocket=websocket, body={})
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
