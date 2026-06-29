import sys
import os

from core.logging import setup_logging
setup_logging()


def _raise_open_file_limit() -> None:
    """Raise the process soft file-descriptor limit toward the hard limit.

    A single voice call holds many concurrent FDs (Twilio/Deepgram/Cartesia/Groq
    websockets, audio recording, plus native libs like cv2/PyAV/aiortc). On macOS
    the default soft limit is only 256; once exhausted, NEW socket creation fails
    and `getaddrinfo` returns "[Errno 8] nodename nor servname provided" — which
    surfaces as STT/TTS reconnect loops mid-call. Linux/k8s defaults are high
    enough that this only bites local dev, but raising it here is harmless and
    makes behavior consistent regardless of how the server is launched.
    """
    try:
        import resource

        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        if soft == resource.RLIM_INFINITY:
            return
        hard_cap = 65536 if hard == resource.RLIM_INFINITY else hard
        # Try progressively smaller targets: some platforms (e.g. macOS) reject
        # a soft limit above kern.maxfilesperproc, so fall back until one sticks.
        for target in (hard_cap, 10240, 4096, 1024):
            if target <= soft or target > hard_cap:
                continue
            try:
                resource.setrlimit(resource.RLIMIT_NOFILE, (target, hard))
                from loguru import logger
                logger.info("Raised open-file limit (RLIMIT_NOFILE) {} -> {}", soft, target)
                return
            except (ValueError, OSError):
                continue
    except Exception as e:  # noqa: BLE001 - best effort; never block startup
        from loguru import logger
        logger.warning("Could not raise open-file limit: {}", e)


_raise_open_file_limit()

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from pipecat.runner.types import WebSocketRunnerArguments

from core.bot import bot
from shared.config import settings
from core.internal.machine import generate_fingerprint
from core.internal.license import init_license_validator, get_license_info
from core.internal.capabilities import init_capabilities, is_ee_enabled, get_capabilities

from core.api.v1 import (
    auth, users, organizations, agent_configs, channels, oauth,
    knowledge_base, agents, mcp_servers, services, tools, dashboard,
    call_logs, call_metrics, sessions, workflows, webrtc
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_v1 = FastAPI()

api_v1.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization", "tenant_id", "Content-Type"],
)

if ee_enabled:
    # EE routers are imported individually because ``ee/api/v1/__init__.py``
    # no longer eagerly imports siblings (some still reference dropped
    # pre-v2 models).
    from ee.api.v1 import auth as ee_auth
    from ee.api.v1 import users as ee_users
    from ee.api.v1 import organizations as ee_organizations
    from ee.api.v1 import agent_configs as ee_agent_configs
    from ee.api.v1 import channels as ee_channels
    from ee.api.v1 import oauth as ee_oauth
    from ee.api.v1 import knowledge_base as ee_knowledge_base
    from ee.api.v1 import agents as ee_agents
    from ee.api.v1 import mcp_servers as ee_mcp_servers
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
    api_v1.include_router(ee_knowledge_base.router, prefix="/knowledge-base", tags=["knowledge-base"])
    api_v1.include_router(ee_agents.router, prefix="/agent", tags=["agent"])
    api_v1.include_router(ee_mcp_servers.router, prefix="/mcp-server", tags=["mcp-server"])
    api_v1.include_router(ee_services.router, prefix="/services", tags=["services"])
    api_v1.include_router(ee_tools.router, prefix="/tool", tags=["tool"])
    api_v1.include_router(ee_dashboard.router, prefix="/dashboard", tags=["dashboard"])
    api_v1.include_router(ee_call_logs.router, prefix="/call-log", tags=["call-log"])
    api_v1.include_router(ee_call_metrics.router, prefix="/call-metrics", tags=["call-metrics"])
    api_v1.include_router(workflows.router, prefix="/workflow", tags=["workflow"])
    api_v1.include_router(webrtc.router, prefix="/webrtc", tags=["webrtc"])
    print("EE edition: auth-schema routes loaded (other routers temporarily disabled pending v2 schema migration)")
else:
    api_v1.include_router(auth.router, prefix="/auth", tags=["auth"])
    api_v1.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
    api_v1.include_router(users.router, prefix="/user", tags=["users"])
    api_v1.include_router(organizations.router, prefix="/organization", tags=["organization"])
    api_v1.include_router(agent_configs.router, prefix="/agent_config", tags=["agent_config"])
    api_v1.include_router(channels.router, prefix="/channel", tags=["channel"])
    api_v1.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
    api_v1.include_router(knowledge_base.router, prefix="/knowledge-base", tags=["knowledge-base"])
    api_v1.include_router(agents.router, prefix="/agent", tags=["agent"])
    api_v1.include_router(mcp_servers.router, prefix="/mcp-server", tags=["mcp-server"])
    api_v1.include_router(services.router, prefix="/services", tags=["services"])
    api_v1.include_router(tools.router, prefix="/tool", tags=["tool"])
    api_v1.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
    api_v1.include_router(call_logs.router, prefix="/call-log", tags=["call-log"])
    api_v1.include_router(call_metrics.router, prefix="/call-metrics", tags=["call-metrics"])
    api_v1.include_router(workflows.router, prefix="/workflow", tags=["workflow"])
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


@app.post("/twiml")
@app.get("/twiml")
async def twiml(request: Request) -> Response:
    host = request.url.hostname or "localhost"
    ws_url = f"wss://{host}/ws"
    from_number = ""
    to_number = ""
    try:
        if request.method == "POST":
            form = await request.form()
            from_number = (form.get("From") or "").strip()
            to_number = (form.get("To") or "").strip()
        else:
            from_number = (request.query_params.get("From") or "").strip()
            to_number = (request.query_params.get("To") or "").strip()
    except Exception:
        pass

    from xml.sax.saxutils import escape as _xml_escape

    params_xml = ""
    if from_number:
        params_xml += f'<Parameter name="from" value="{_xml_escape(from_number)}" />'
    if to_number:
        params_xml += f'<Parameter name="to" value="{_xml_escape(to_number)}" />'

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        '<Connect>'
        f'<Stream url="{ws_url}">{params_xml}</Stream>'
        '</Connect>'
        '</Response>'
    )
    return Response(content=xml, media_type="application/xml")


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    runner_args = WebSocketRunnerArguments(websocket=websocket, body={})
    try:
        await bot(runner_args)
    except Exception as exc:
        print(f"[/ws] bot crashed: {exc}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
