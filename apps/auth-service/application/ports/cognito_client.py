from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from ...domain.entities.user import User


class CognitoClient(ABC):
    """Port for Cognito user pool operations"""
    
    @abstractmethod
    async def initiate_auth(
        self,
        username: str,
        password: str,
        auth_flow: str = "USER_PASSWORD_AUTH"
    ) -> Dict[str, Any]:
        """Initiate authentication with Cognito"""
        pass
    
    @abstractmethod
    async def initiate_srp_auth(
        self,
        username: str,
        srp_a: str
    ) -> Dict[str, Any]:
        """Initiate SRP authentication"""
        pass
    
    @abstractmethod
    async def respond_to_srp_challenge(
        self,
        username: str,
        challenge_name: str,
        session: str,
        challenge_responses: Dict[str, str]
    ) -> Dict[str, Any]:
        """Respond to SRP challenge"""
        pass
    
    @abstractmethod
    async def sign_up(
        self,
        username: str,
        password: str,
        email: str,
        given_name: Optional[str] = None,
        family_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sign up a new user"""
        pass
    
    @abstractmethod
    async def confirm_sign_up(
        self,
        username: str,
        confirmation_code: str
    ) -> Dict[str, Any]:
        """Confirm user sign up with verification code"""
        pass
    
    @abstractmethod
    async def resend_confirmation_code(
        self,
        username: str
    ) -> Dict[str, Any]:
        """Resend confirmation code"""
        pass
    
    @abstractmethod
    async def forgot_password(
        self,
        username: str
    ) -> Dict[str, Any]:
        """Initiate forgot password flow"""
        pass
    
    @abstractmethod
    async def confirm_forgot_password(
        self,
        username: str,
        confirmation_code: str,
        new_password: str
    ) -> Dict[str, Any]:
        """Confirm forgot password with new password"""
        pass
    
    @abstractmethod
    async def refresh_token(
        self,
        refresh_token: str
    ) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        pass
    
    @abstractmethod
    async def get_user(
        self,
        access_token: str
    ) -> Dict[str, Any]:
        """Get user information using access token"""
        pass
    
    @abstractmethod
    async def admin_get_user(
        self,
        username: str
    ) -> Dict[str, Any]:
        """Get user information using admin privileges"""
        pass
    
    @abstractmethod
    async def global_sign_out(
        self,
        access_token: str
    ) -> None:
        """Sign out user from all devices"""
        pass
    
    @abstractmethod
    async def get_hosted_ui_url(
        self,
        redirect_uri: str,
        state: Optional[str] = None,
        identity_provider: Optional[str] = None
    ) -> str:
        """Get Cognito Hosted UI URL for social login"""
        pass
    
    @abstractmethod
    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        pass