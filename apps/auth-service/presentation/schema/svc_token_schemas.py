from pydantic import BaseModel


class ServiceTokenRequest(BaseModel):
    """Service token request"""

    client_id: str
    client_secret: str
    sub_spn: str
    scope: str
    actor_sub: str | None = None
    actor_scope: str | None = None
    actor_roles: list[str] | None = None


class ServiceTokenResponse(BaseModel):
    """Service token response"""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
