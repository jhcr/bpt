from abc import ABC, abstractmethod
from typing import Optional
from ...domain.entities.session import Session, CipherSession


class SessionRepository(ABC):
    """Port for session storage operations"""
    
    @abstractmethod
    async def save_session(self, session: Session) -> None:
        """Save a user session"""
        pass
    
    @abstractmethod
    async def get_session(self, sid: str) -> Optional[Session]:
        """Get a session by ID"""
        pass
    
    @abstractmethod
    async def delete_session(self, sid: str) -> bool:
        """Delete a session by ID"""
        pass
    
    @abstractmethod
    async def update_session(self, session: Session) -> None:
        """Update an existing session"""
        pass
    
    @abstractmethod
    async def get_sessions_by_user(self, user_id: str) -> list[Session]:
        """Get all sessions for a user"""
        pass
    
    @abstractmethod
    async def delete_sessions_by_user(self, user_id: str) -> int:
        """Delete all sessions for a user, return count deleted"""
        pass


class CipherSessionRepository(ABC):
    """Port for cipher session storage operations"""
    
    @abstractmethod
    async def save_cipher_session(self, cipher_session: CipherSession) -> None:
        """Save a cipher session"""
        pass
    
    @abstractmethod
    async def get_cipher_session(self, sid: str) -> Optional[CipherSession]:
        """Get a cipher session by ID"""
        pass
    
    @abstractmethod
    async def delete_cipher_session(self, sid: str) -> bool:
        """Delete a cipher session by ID"""
        pass