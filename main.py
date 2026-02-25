from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.api.v1 import auth, users, organizations, api_keys, services, service_providers, agents, agent_configs, agent_phone_numbers, models as models_router, generated_api_keys, channels
import core.models

app = FastAPI(title="Tone API - Core", version="1.0.0")

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
api_v1.include_router(agent_phone_numbers.router, prefix="/agent_phone_number", tags=["agent_phone_number"])
api_v1.include_router(models_router.router, prefix="/model", tags=["model"])
api_v1.include_router(generated_api_keys.router, prefix="/generated-api-keys", tags=["generated-api-keys"])
api_v1.include_router(channels.router, prefix="/channel", tags=["channel"])

app.mount("/api/v1", api_v1)


@app.get("/")
def root():
    return {"message": "Tone API - Core Edition", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok", "edition": "core"}


@app.get("/environment")
def environment():
    return {"environment": settings.ENVIRONMENT}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
