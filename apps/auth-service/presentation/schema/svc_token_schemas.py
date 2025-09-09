from pydantic import BaseModel
from typing import Optional, List


class ServiceTokenRequest(BaseModel):
    """Service token request"""
    client_id: str
    client_secret: str
    sub_spn: str
    scope: str
    actor_sub: Optional[str] = None
    actor_scope: Optional[str] = None
    actor_roles: Optional[List[str]] = None


class ServiceTokenResponse(BaseModel):
    """Service token response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int