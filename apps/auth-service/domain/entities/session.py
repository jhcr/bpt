from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Session:
    """Domain entity representing a user session"""
    
    sid: str
    user_id: str
    cognito_sub: str
    refresh_token: str
    created_at: datetime
    expires_at: datetime
    last_accessed: datetime
    version: int
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if session is valid (not expired)"""
        return not self.is_expired()
    
    def update_last_accessed(self) -> "Session":
        """Update last accessed timestamp"""
        return Session(
            sid=self.sid,
            user_id=self.user_id,
            cognito_sub=self.cognito_sub,
            refresh_token=self.refresh_token,
            created_at=self.created_at,
            expires_at=self.expires_at,
            last_accessed=datetime.utcnow(),
            version=self.version + 1,
            device_info=self.device_info,
            ip_address=self.ip_address,
            user_agent=self.user_agent,
        )


@dataclass
class CipherSession:
    """Session for password encryption using ECDH"""
    
    sid: str
    server_private_key_pem: bytes
    server_public_key_jwk: dict
    created_at: datetime
    expires_at: datetime
    
    def is_expired(self) -> bool:
        """Check if cipher session is expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if cipher session is valid"""
        return not self.is_expired()