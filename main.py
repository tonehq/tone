import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import settings
from core.internal.machine import generate_fingerprint
from core.internal.license import init_license_validator, get_license_info
from core.internal.capabilities import init_capabilities, is_ee_enabled, get_capabilities

from core.api.v1 import (
    auth, users, organizations, api_keys, services,
    service_providers, agents, agent_configs,
    channel_phone_numbers, models as models_router,
    generated_api_keys, channels, voices
)
import core.models

fingerprint = generate_fingerprint(settings.DATABASE_URL)
init_license_validator(settings.LICENSE_KEY)
license_info = get_license_info(fingerprint)
capabilities = init_capabilities(fingerprint)

if not license_info.is_valid and settings.LICENSE_KEY:
    print(f"License validation failed: {license_info.validation_error}")
    if license_info.validation_error == "fingerprint_mismatch":
        print("License is bound to a different instance.")
        sys.exit(1)

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

api_v1.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1.include_router(users.router, prefix="/user", tags=["users"])
api_v1.include_router(organizations.router, prefix="/organization", tags=["organization"])
api_v1.include_router(service_providers.router, prefix="/service-providers", tags=["service-providers"])
api_v1.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
api_v1.include_router(services.router, prefix="/services", tags=["services"])
api_v1.include_router(agents.router, prefix="/agent", tags=["agent"])
api_v1.include_router(agent_configs.router, prefix="/agent_config", tags=["agent_config"])
api_v1.include_router(channel_phone_numbers.router, prefix="/channel_phone_number", tags=["channel_phone_number"])
api_v1.include_router(models_router.router, prefix="/model", tags=["model"])
api_v1.include_router(generated_api_keys.router, prefix="/generated-api-keys", tags=["generated-api-keys"])
api_v1.include_router(channels.router, prefix="/channel", tags=["channel"])
api_v1.include_router(voices.router, prefix="/voice", tags=["voice"])

if ee_enabled:
    try:
        from ee.api.v1 import auth as ee_auth
        from ee.api.v1 import organizations as ee_organizations

        api_v1.include_router(ee_auth.router, prefix="/ee/auth", tags=["ee-auth"])
        api_v1.include_router(ee_organizations.router, prefix="/ee/org", tags=["ee-org"])
        print(f"EE routes loaded successfully")
    except ImportError as e:
        print(f"Failed to load EE routes: {e}")


@api_v1.get("/capabilities", tags=["system"])
def get_capabilities_endpoint():
    return {"capabilities": get_capabilities(), "edition": edition, "ee_enabled": ee_enabled}


app.mount("/api/v1", api_v1)


@app.get("/")
def root():
    return {
        "message": f"Tone API - {edition.title()} Edition",
        "version": "1.0.0",
        "edition": edition,
    }


@app.get("/health")
def health():
    return {"status": "ok", "edition": edition}


@app.get("/environment")
def environment():
    return {"environment": settings.ENVIRONMENT}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
