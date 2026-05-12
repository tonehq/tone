import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import settings
from core.internal.machine import generate_fingerprint
from core.internal.license import init_license_validator, get_license_info
from core.internal.capabilities import init_capabilities, is_ee_enabled, get_capabilities

from core.api.v1 import (
    auth, users, organizations, api_keys, services,
    service_providers, agents, agent_configs,
    agent_channel_phone_numbers, channel_phone_numbers,
    models as models_router,
    generated_api_keys, channels, voices, call_logs,
    telephony, documents, tools, oauth, mcp_servers,
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
    from ee.api.v1 import (
        auth as ee_auth,
        users as ee_users,
        organizations as ee_organizations,
        service_providers as ee_service_providers,
        api_keys as ee_api_keys,
        services as ee_services,
        agents as ee_agents,
        agent_configs as ee_agent_configs,
        agent_channel_phone_numbers as ee_agent_channel_phone_numbers,
        channel_phone_numbers as ee_channel_phone_numbers,
        models as ee_models,
        generated_api_keys as ee_generated_api_keys,
        channels as ee_channels,
        voices as ee_voices,
        call_logs as ee_call_logs,
        telephony as ee_telephony,
        documents as ee_documents,
        tools as ee_tools,
        oauth as ee_oauth,
        mcp_servers as ee_mcp_servers,
    )

    api_v1.include_router(ee_auth.router, prefix="/auth", tags=["auth"])
    api_v1.include_router(ee_users.router, prefix="/user", tags=["users"])
    api_v1.include_router(ee_organizations.router, prefix="/organization", tags=["organization"])
    api_v1.include_router(ee_service_providers.router, prefix="/service-providers", tags=["service-providers"])
    api_v1.include_router(ee_api_keys.router, prefix="/api-keys", tags=["api-keys"])
    api_v1.include_router(ee_services.router, prefix="/services", tags=["services"])
    api_v1.include_router(ee_agents.router, prefix="/agent", tags=["agent"])
    api_v1.include_router(ee_agent_configs.router, prefix="/agent_config", tags=["agent_config"])
    api_v1.include_router(ee_agent_channel_phone_numbers.router, prefix="/agent_channel_phone_number", tags=["agent_channel_phone_number"])
    api_v1.include_router(ee_channel_phone_numbers.router, prefix="/channel_phone_number", tags=["channel_phone_number"])
    api_v1.include_router(ee_models.router, prefix="/model", tags=["model"])
    api_v1.include_router(ee_generated_api_keys.router, prefix="/generated-api-keys", tags=["generated-api-keys"])
    api_v1.include_router(ee_channels.router, prefix="/channel", tags=["channel"])
    api_v1.include_router(ee_voices.router, prefix="/voice", tags=["voice"])
    api_v1.include_router(ee_call_logs.router, prefix="/call-log", tags=["call-log"])
    api_v1.include_router(ee_documents.router, prefix="/document", tags=["document"])
    api_v1.include_router(ee_tools.router, prefix="/tool", tags=["tool"])
    api_v1.include_router(ee_oauth.router, prefix="/oauth", tags=["oauth"])
    api_v1.include_router(ee_mcp_servers.router, prefix="/mcp-server", tags=["mcp-server"])
    print("EE edition: Multi-tenant routes loaded")
else:
    api_v1.include_router(auth.router, prefix="/auth", tags=["auth"])
    api_v1.include_router(users.router, prefix="/user", tags=["users"])
    api_v1.include_router(organizations.router, prefix="/organization", tags=["organization"])
    api_v1.include_router(service_providers.router, prefix="/service-providers", tags=["service-providers"])
    api_v1.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
    api_v1.include_router(services.router, prefix="/services", tags=["services"])
    api_v1.include_router(agents.router, prefix="/agent", tags=["agent"])
    api_v1.include_router(agent_configs.router, prefix="/agent_config", tags=["agent_config"])
    api_v1.include_router(agent_channel_phone_numbers.router, prefix="/agent_channel_phone_number", tags=["agent_channel_phone_number"])
    api_v1.include_router(channel_phone_numbers.router, prefix="/channel_phone_number", tags=["channel_phone_number"])
    api_v1.include_router(models_router.router, prefix="/model", tags=["model"])
    api_v1.include_router(generated_api_keys.router, prefix="/generated-api-keys", tags=["generated-api-keys"])
    api_v1.include_router(channels.router, prefix="/channel", tags=["channel"])
    api_v1.include_router(voices.router, prefix="/voice", tags=["voice"])
    api_v1.include_router(call_logs.router, prefix="/call-log", tags=["call-log"])
    api_v1.include_router(documents.router, prefix="/document", tags=["document"])
    api_v1.include_router(tools.router, prefix="/tool", tags=["tool"])
    api_v1.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
    api_v1.include_router(mcp_servers.router, prefix="/mcp-server", tags=["mcp-server"])
    print("Core edition: Single-tenant routes loaded")


@api_v1.get("/capabilities", tags=["system"])
def get_capabilities_endpoint():
    return {"capabilities": get_capabilities(), "edition": edition, "ee_enabled": ee_enabled}


app.mount("/api/v1", api_v1)

# Public telephony WebSocket — no auth required, mounted at root for provider compatibility
if ee_enabled:
    app.include_router(ee_telephony.router, tags=["telephony"])
else:
    app.include_router(telephony.router, tags=["telephony"])


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
