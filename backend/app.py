from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import uvicorn
import os
import logging

# Import only auth router
from src.controller.auth_controller import router as auth_router

from src.settings import settings, load_config

# Load environment configuration at startup
load_config()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable SQLAlchemy logging noise
logging.getLogger('sqlalchemy.engine').propagate = False
logging.getLogger('sqlalchemy.pool').propagate = False
logging.getLogger('sqlalchemy.dialects').propagate = False
logging.getLogger('sqlalchemy.orm').propagate = False

app = FastAPI(
    title="Auth & B2B User Management API",
    description="Authentication and B2B User Management System with JWT",
    version="1.0.0"
)
adminApp = FastAPI()
apiApp = FastAPI()

def set_env(env: str):
    os.environ["ENV"] = env
    print(f"ENV set from command line argument: {env}")


if __name__ == "__main__":
    import sys

    # Check for --env argument in sys.argv
    env_arg = None
    for i, arg in enumerate(sys.argv):
        if arg == "--env" and i + 1 < len(sys.argv):
            env_arg = sys.argv[i + 1]
            break
        elif arg.startswith("--env="):
            env_arg = arg.split("=", 1)[1]
            break

    if env_arg:
        os.environ["ENV"] = env_arg
        print(f"ENV set from command line argument: {env_arg}")
    else:
        print(f"No --env argument found. ENV is: {os.getenv('ENV', 'not_set')}")
    
    if env_arg:
        set_env(env_arg)
    
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)


def prepare():
    """Initialize application components"""
    logger.info("Preparing application...")
    logger.info("Application preparation completed")


def setup_routes():
    """Setup all application routes"""
    # CORS middleware
    apiApp.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include only auth router
    apiApp.include_router(auth_router)


# Initialize application
prepare()
setup_routes()

app.mount('/api/v1', apiApp)
app.mount('/admin/v1', adminApp)







# Health check endpoints
@app.get("/health")
def health():
    """Health check endpoint"""
    env = os.getenv("ENV", "not_set")
    config_url = os.getenv("CUSTOMCONNSTR_CONFIG_URL", "not_set")
    return {
        "status": "ok", 
        "env": env, 
        "config_url": "***" if config_url != "not_set" else config_url,
        "services": ["auth", "organizations", "users", "permissions"]
    }


@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "message": "Auth & B2B User Management API is running",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/v1/auth/*",
            "organizations": "/api/v1/org/*",
            "users": "/api/v1/user/*",
            "organization_management": "/api/v1/organization/*",
            "permissions": "/api/v1/permissions/*"
        }
    }


@app.get("/environment")
def get_environment():
    """Get the current environment configuration"""
    env = os.getenv("ENVIRONMENT", "dev")
    logger.info("Environment endpoint accessed")
    logger.info(f"Environment: {env}")
    return {
        "environment": env,
        "settings": settings.__dict__ if hasattr(settings, '__dict__') else str(settings)
    }


# Debug endpoint to help see what paths are being received
@app.get("/debug")
def debug_info(request: Request):
    """Debug endpoint for request information"""
    return {
        "url": str(request.url),
        "base_url": str(request.base_url),
        "root_path": request.scope.get("root_path", ""),
        "path": request.scope.get("path", ""),
        "method": request.method,
        "headers": dict(request.headers)
    }


# Additional endpoint for API documentation
@app.get("/api/endpoints")
def list_endpoints():
    """List all available API endpoints"""
    return {
        "authentication": {
            "POST /api/v1/auth/signup": "User signup with email/password",
            "POST /api/v1/auth/signup_with_firebase": "User signup with Firebase",
            "GET /api/v1/auth/resend_verification_email": "Resend email verification",
            "GET /api/v1/auth/verify_user_email": "Verify user email",
            "POST /api/v1/auth/login": "User login",
            "GET /api/v1/auth/forget-password": "Send password reset email",
            "GET /api/v1/auth/acceptForgotPassword": "Reset password",
            "POST /api/v1/auth/switch_organization": "Switch organization context"
        },
        "organizations": {
            "GET /api/v1/org/get_associated_tenants": "Get user organizations",
            "POST /api/v1/org/create_tenants": "Create new organization"
        },
        "users": {
            "POST /api/v1/user/get_all_users_for_organization": "Get organization members"
        },
        "organization_management": {
            "POST /api/v1/organization/invite_user_to_organization": "Invite user to org",
            "DELETE /api/v1/organization/remove_user_from_organization": "Remove user from org",
            "POST /api/v1/organization/update_member_role": "Update member role"
        },
        "permissions": {
            "GET /api/v1/permissions/get_roles_by_scope": "Get available roles"
        }
    }