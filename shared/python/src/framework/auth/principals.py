from dataclasses import dataclass


@dataclass
class Principal:
    """Represents an authenticated principal (user or service)"""

    sub: str
    scopes: list[str]
    roles: list[str]
    token_use: str = "access"  # "access" or "svc"

    # User-specific fields
    sid: str | None = None
    sidv: int | None = None
    idp: str | None = None
    cognito_sub: str | None = None
    tenant_id: str | None = None

    # Service token fields
    svc_sub: str | None = None
    actor_sub: str | None = None
    actor_scope: str | None = None
    actor_roles: list[str] | None = None

    def has_scope(self, scope: str) -> bool:
        """Check if principal has a specific scope"""
        return scope in self.scopes

    def has_any_scope(self, scopes: list[str]) -> bool:
        """Check if principal has any of the given scopes"""
        return any(scope in self.scopes for scope in scopes)

    def has_role(self, role: str) -> bool:
        """Check if principal has a specific role"""
        return role in self.roles

    def is_service_token(self) -> bool:
        """Check if this is a service token"""
        return self.token_use == "svc"

    def is_user_token(self) -> bool:
        """Check if this is a user access token"""
        return self.token_use == "access"

    def get_actor_sub(self) -> str | None:
        """Get the subject of the acting user (for service tokens)"""
        return self.actor_sub if self.is_service_token() else self.sub

    def get_actor_scopes(self) -> list[str]:
        """Get the scopes of the acting user"""
        if self.is_service_token() and self.actor_scope:
            return self.actor_scope.split()
        return self.scopes

    def get_actor_roles(self) -> list[str]:
        """Get the roles of the acting user"""
        return self.actor_roles or [] if self.is_service_token() else self.roles


def create_user_principal(claims: dict) -> Principal:
    """Create a Principal from user JWT claims"""
    return Principal(
        sub=claims["sub"],
        scopes=claims.get("scope", "").split(),
        roles=claims.get("roles", []),
        token_use="access",
        sid=claims.get("sid"),
        sidv=claims.get("sidv"),
        idp=claims.get("idp"),
        cognito_sub=claims.get("cognito_sub"),
        tenant_id=claims.get("tenant_id"),
    )


def create_service_principal(claims: dict) -> Principal:
    """Create a Principal from service JWT claims"""
    act = claims.get("act", {}) if isinstance(claims.get("act"), dict) else {}

    return Principal(
        sub=claims["sub"],
        scopes=claims.get("scope", "").split(),
        roles=[],
        token_use="svc",
        svc_sub=claims["sub"],
        actor_sub=act.get("sub"),
        actor_scope=act.get("scope"),
        actor_roles=act.get("roles", []),
    )
