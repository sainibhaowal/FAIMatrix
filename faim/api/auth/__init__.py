# =============================================================================
# FAIM API - Authentication Module
# =============================================================================
# Contains: OTP auth, JWT management, API keys, user provisioning, email
# =============================================================================

__all__ = [
    # OTP Authentication
    "create_otp",
    "verify_otp",
    "send_otp_email",
    # JWT
    "create_access_token",
    "create_refresh_token",
    "verify_access_token",
    "verify_refresh_token",
    "get_current_user",
    # API Keys (database-backed)
    "keys_router",
    "verify_key_from_db",
    "require_api_key",
    "require_admin_or_api_key",
    "verify_graph_access",
    "verify_db_api_key",
    # User
    "user_router",
    "get_current_user_oidc",
    # Email
    "send_verification_email",
    "send_password_reset_email",
]

# OTP Authentication
from faim.api.auth.auth import (
    require_admin_or_api_key,
    require_api_key,
    verify_graph_access,
)

# Email Services
from faim.api.auth.email import (
    send_otp_email,
    send_password_reset_email,
    send_verification_email,
)

# JWT Authentication
from faim.api.auth.jwt_auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    verify_access_token,
    verify_refresh_token,
)

# API Key Management (database-backed)
from faim.api.auth.keys import router as keys_router
from faim.api.auth.keys import verify_key_from_db
from faim.api.auth.otp import create_otp, verify_otp

# User Provisioning
from faim.api.auth.user import router as user_router
from faim.api.middleware.auth_middleware import get_current_user_oidc, verify_db_api_key
