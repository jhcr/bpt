from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class User:
    """User profile domain entity"""
    
    id: str
    cognito_sub: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        # Ensure id is a string
        if isinstance(self.id, uuid.UUID):
            self.id = str(self.id)
    
    @classmethod
    def create(
        cls,
        cognito_sub: str,
        email: str,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        phone: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> "User":
        """Create a new user entity"""
        now = datetime.utcnow()
        
        return cls(
            id=user_id or str(uuid.uuid4()),
            cognito_sub=cognito_sub,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            phone=phone,
            is_active=True,
            created_at=now,
            updated_at=now
        )
    
    def update(
        self,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        phone: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> "User":
        """Create updated copy of user"""
        return User(
            id=self.id,
            cognito_sub=self.cognito_sub,
            email=email if email is not None else self.email,
            display_name=display_name if display_name is not None else self.display_name,
            avatar_url=avatar_url if avatar_url is not None else self.avatar_url,
            phone=phone if phone is not None else self.phone,
            is_active=is_active if is_active is not None else self.is_active,
            created_at=self.created_at,
            updated_at=datetime.utcnow()
        )
    
    def deactivate(self) -> "User":
        """Create deactivated copy of user"""
        return self.update(is_active=False)
    
    def is_email_valid(self) -> bool:
        """Basic email validation"""
        return "@" in self.email and "." in self.email.split("@")[1]
    
    def get_display_name_or_email(self) -> str:
        """Get display name or fallback to email"""
        return self.display_name or self.email.split("@")[0]