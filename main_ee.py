from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ee.config import ee_settings
from ee.api.v1 import auth, users, organizations

app = FastAPI(title="Tone API - Enterprise", version="1.0.0")

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
api_v1.include_router(organizations.router, prefix="/org", tags=["org"])
api_v1.include_router(organizations.router, prefix="/organization", tags=["organization"])

app.mount("/api/v1", api_v1)


@app.get("/")
def root():
    return {"message": "Tone API - Enterprise Edition", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok", "edition": "enterprise"}


@app.get("/environment")
def environment():
    return {"environment": ee_settings.ENVIRONMENT}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
