from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class User:
    """Domain entity representing a user"""
    
    id: str
    cognito_sub: str
    email: str
    email_verified: bool
    phone_number: Optional[str] = None
    phone_verified: bool = False
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    preferred_username: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None
    zoneinfo: Optional[str] = None
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    enabled: bool = True
    user_status: str = "CONFIRMED"
    mfa_options: List[dict] = None
    
    def __post_init__(self):
        if self.mfa_options is None:
            self.mfa_options = []
    
    @property
    def display_name(self) -> str:
        """Get display name for the user"""
        if self.given_name and self.family_name:
            return f"{self.given_name} {self.family_name}"
        elif self.given_name:
            return self.given_name
        elif self.preferred_username:
            return self.preferred_username
        else:
            return self.email.split("@")[0]
    
    def is_active(self) -> bool:
        """Check if user is active"""
        return self.enabled and self.user_status == "CONFIRMED"
    
    def is_email_verified(self) -> bool:
        """Check if user's email is verified"""
        return self.email_verified
    
    def has_mfa_enabled(self) -> bool:
        """Check if user has MFA enabled"""
        return len(self.mfa_options) > 0


@dataclass
class AuthenticatedUser:
    """Represents an authenticated user with token information"""
    
    user: User
    access_token: str
    refresh_token: Optional[str]
    id_token: Optional[str]
    token_type: str = "Bearer"
    expires_in: int = 900  # 15 minutes
    auth_time: datetime = None
    amr: List[str] = None  # Authentication Methods References
    idp: str = "cognito"  # Identity Provider
    
    def __post_init__(self):
        if self.auth_time is None:
            self.auth_time = datetime.utcnow()
        if self.amr is None:
            self.amr = ["pwd"]