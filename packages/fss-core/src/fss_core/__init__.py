"""FSS Core — FSS protocol primitives: provenance, integrity, auth, FIT."""

from fss_core.auth import (
    ApiKeyProvider,
    AuthIdentity,
    AuthProvider,
    AuthResult,
    NoAuthProvider,
    OAuthJWTProvider,
    TokenAuthProvider,
    check_auth,
    create_auth_provider,
)
from fss_core.errors import (
    FSS_AUTH_DENIED,
    FSS_AUTH_REQUIRED,
    FSS_DATASET_UNAVAILABLE,
    FSS_EXECUTION_FAILED,
    FSS_EXECUTION_INTERRUPTED,
    FSS_INTERNAL_ERROR,
    FSS_PARAM_INVALID,
    FSS_RATE_LIMITED,
    FSS_REPLAY_REJECTED,
    FSS_TOOL_UNAVAILABLE,
    AuthError,
    ExtensionError,
    FSSCoreError,
    FSSError,
    IOLimitError,
    RateLimitError,
    SanitizationError,
    ValidationError,
)
from fss_core.integrity import (
    build_jwks,
    check_jcs_required,
    compute_cai,
    compute_json_cai,
    compute_kb_version_id,
    ensure_signing_key_pair,
    load_signing_key,
    sign_provenance,
    sign_provenance_full,
    validate_cai,
)
from fss_core.provenance import build_provenance_record

__version__ = "0.1.0"

__all__ = [
    # errors
    "FSSCoreError",
    "FSSError",
    "ValidationError",
    "SanitizationError",
    "RateLimitError",
    "IOLimitError",
    "AuthError",
    "ExtensionError",
    # FSS error codes
    "FSS_AUTH_REQUIRED",
    "FSS_AUTH_DENIED",
    "FSS_PARAM_INVALID",
    "FSS_REPLAY_REJECTED",
    "FSS_TOOL_UNAVAILABLE",
    "FSS_DATASET_UNAVAILABLE",
    "FSS_RATE_LIMITED",
    "FSS_EXECUTION_INTERRUPTED",
    "FSS_EXECUTION_FAILED",
    "FSS_INTERNAL_ERROR",
    # auth
    "ApiKeyProvider",
    "AuthIdentity",
    "AuthProvider",
    "AuthResult",
    "NoAuthProvider",
    "OAuthJWTProvider",
    "TokenAuthProvider",
    "check_auth",
    "create_auth_provider",
    # integrity
    "build_jwks",
    "check_jcs_required",
    "compute_cai",
    "compute_json_cai",
    "compute_kb_version_id",
    "ensure_signing_key_pair",
    "load_signing_key",
    "sign_provenance",
    "sign_provenance_full",
    "validate_cai",
    # provenance
    "build_provenance_record",
]
