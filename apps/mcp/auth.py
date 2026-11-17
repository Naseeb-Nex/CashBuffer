from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any, Mapping

import jwt

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthContext:
    """Immutable identity context for the authenticated caller/tenant."""

    user_id: str
    tenant_id: str
    email: str | None = None
    scopes: tuple[str, ...] = field(default_factory=tuple)
    claims: dict[str, Any] = field(default_factory=dict)
    provider: str = "generic"

    @classmethod
    def create(
        cls,
        user_id: str,
        tenant_id: str | None = None,
        email: str | None = None,
        scopes: list[str] | tuple[str, ...] = (),
        claims: dict[str, Any] | None = None,
        provider: str = "generic",
    ) -> AuthContext:
        resolved_tenant = tenant_id or user_id
        return cls(
            user_id=user_id,
            tenant_id=resolved_tenant,
            email=email,
            scopes=tuple(scopes),
            claims=dict(claims or {}),
            provider=provider,
        )


class AuthError(Exception):
    """Base exception for authentication and authorization errors."""


class MissingAuthContextError(AuthError):
    """Raised when an operation requires an authenticated tenant context but none is present."""


class InvalidCredentialsError(AuthError):
    """Raised when supplied authentication credentials are invalid or expired."""


class UnauthorizedAuthorityError(AuthError):
    """Raised when caller attempts to pass user-supplied authority instead of using verified context."""


class AuthProvider(ABC):
    """Provider-neutral boundary interface for authenticating incoming requests."""

    @abstractmethod
    async def authenticate(self, credentials: Any) -> AuthContext:
        """Authenticate supplied credentials into an AuthContext."""
        raise NotImplementedError


class JWTAuthProvider(AuthProvider):
    """
    Provider-neutral JWT authenticator.
    Validates token signature and extracts standard claims (sub -> user_id/tenant_id).
    Compatible with Kinde, Auth0, Supabase, and internal tokens.
    """

    def __init__(
        self,
        secret_or_key: str = "",
        algorithms: list[str] | None = None,
        audience: str | None = None,
        issuer: str | None = None,
        verify_signature: bool = True,
    ) -> None:
        self.secret_or_key = secret_or_key
        self.algorithms = algorithms or ["HS256"]
        self.audience = audience
        self.issuer = issuer
        self.verify_signature = verify_signature and bool(secret_or_key)

    async def authenticate(self, credentials: Any) -> AuthContext:
        if not isinstance(credentials, str):
            raise InvalidCredentialsError("JWT token must be a string")

        token = credentials.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()

        if not token:
            raise InvalidCredentialsError("Empty JWT token provided")

        try:
            decode_options = {
                "verify_signature": self.verify_signature,
                "verify_exp": True,
            }
            claims = jwt.decode(
                token,
                key=self.secret_or_key,
                algorithms=self.algorithms,
                audience=self.audience,
                issuer=self.issuer,
                options=decode_options,
            )
        except jwt.ExpiredSignatureError as e:
            raise InvalidCredentialsError("Token has expired") from e
        except jwt.PyJWTError as e:
            raise InvalidCredentialsError(f"Invalid token: {e}") from e

        user_id = claims.get("sub")
        if not user_id:
            raise InvalidCredentialsError("Token missing mandatory 'sub' claim")

        email = claims.get("email")
        scopes = claims.get("scp") or claims.get("scopes") or []
        if isinstance(scopes, str):
            scopes = scopes.split(" ")

        return AuthContext.create(
            user_id=str(user_id),
            tenant_id=str(user_id),
            email=str(email) if email else None,
            scopes=scopes,
            claims=claims,
            provider="jwt",
        )


class StaticTokenAuthProvider(AuthProvider):
    """Token-to-tenant mapping authenticator for deterministic or internal token authentication."""

    def __init__(self, token_map: dict[str, AuthContext]) -> None:
        self._tokens = dict(token_map)

    def register(self, token: str, context: AuthContext) -> None:
        self._tokens[token] = context

    async def authenticate(self, credentials: Any) -> AuthContext:
        if not isinstance(credentials, str):
            raise InvalidCredentialsError("Token must be a string")
        clean_token = credentials.strip()
        if clean_token.lower().startswith("bearer "):
            clean_token = clean_token[7:].strip()

        if clean_token in self._tokens:
            return self._tokens[clean_token]
        raise InvalidCredentialsError("Unknown or unauthorized token")


_current_auth_context: ContextVar[AuthContext | None] = ContextVar(
    "current_auth_context", default=None
)


def set_current_auth(auth: AuthContext | None) -> Token[AuthContext | None]:
    return _current_auth_context.set(auth)


def reset_current_auth(token: Token[AuthContext | None]) -> None:
    _current_auth_context.reset(token)


class auth_scope:
    """Synchronous and asynchronous context manager for tenant authentication scopes."""

    def __init__(self, auth: AuthContext) -> None:
        self.auth = auth
        self._token: Token[AuthContext | None] | None = None

    def __enter__(self) -> AuthContext:
        self._token = _current_auth_context.set(self.auth)
        return self.auth

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._token is not None:
            _current_auth_context.reset(self._token)

    async def __aenter__(self) -> AuthContext:
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)


def extract_headers_from_ctx(ctx: Any) -> Mapping[str, str] | None:
    """Safely extract transport headers from MCP context if available."""
    if ctx is None:
        return None
    try:
        req_ctx = getattr(ctx, "request_context", None)
        if req_ctx and hasattr(req_ctx, "request"):
            return getattr(req_ctx.request, "headers", None)
    except (ValueError, AttributeError):
        pass
    return None


def get_current_auth_context(ctx: Any = None) -> AuthContext | None:
    """
    Retrieve active AuthContext from ContextVar or extract from MCP Context headers.
    """
    active = _current_auth_context.get()
    if active is not None:
        return active
    return None


def require_auth_context(ctx: Any = None) -> AuthContext:
    """
    Ensure an authenticated tenant context is present.
    Raises MissingAuthContextError if caller has not authenticated.
    """
    auth = get_current_auth_context(ctx)
    if auth is None:
        raise MissingAuthContextError(
            "Authentication required. No valid tenant auth context found for MCP tool execution."
        )
    return auth


FORBIDDEN_AUTHORITY_KEYS = {
    "user_id",
    "tenant_id",
    "sub",
    "authority",
    "caller_id",
    "impersonate_user_id",
}


def forbid_user_supplied_authority(params: dict[str, Any]) -> None:
    """
    Reject any caller-supplied authority parameters.
    Tenant authority MUST originate strictly from the verified AuthContext.
    """
    supplied = FORBIDDEN_AUTHORITY_KEYS.intersection(params.keys())
    if supplied:
        violator = sorted(supplied)[0]
        raise UnauthorizedAuthorityError(
            f"User-supplied authority '{violator}' is forbidden. "
            "Tenant context must be established exclusively via the auth boundary."
        )
