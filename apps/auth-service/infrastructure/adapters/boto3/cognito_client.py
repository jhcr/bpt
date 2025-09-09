import boto3
from typing import Dict, Any, Optional
from ....application.ports.cognito_client import CognitoClient
import structlog

logger = structlog.get_logger(__name__)


class CognitoClientAdapter(CognitoClient):
    """AWS Cognito client adapter using boto3"""
    
    def __init__(self, user_pool_id: str, client_id: str, client_secret: str, region: str = "us-east-1"):
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.region = region
        
        self.client = boto3.client("cognito-idp", region_name=region)
        
        logger.info("Cognito client initialized", 
                   user_pool_id=user_pool_id, client_id=client_id, region=region)
    
    async def initiate_auth(
        self,
        username: str,
        password: str,
        auth_flow: str = "USER_PASSWORD_AUTH"
    ) -> Dict[str, Any]:
        """Initiate authentication with Cognito"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow=auth_flow,
                AuthParameters={
                    "USERNAME": username,
                    "PASSWORD": password,
                    "SECRET_HASH": self._calculate_secret_hash(username) if self.client_secret else None
                }
            )
            
            logger.debug("Cognito auth initiated", username=username, auth_flow=auth_flow)
            return response
            
        except Exception as e:
            logger.error("Cognito auth failed", username=username, error=str(e))
            raise
    
    async def initiate_srp_auth(
        self,
        username: str,
        srp_a: str
    ) -> Dict[str, Any]:
        """Initiate SRP authentication"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow="USER_SRP_AUTH",
                AuthParameters={
                    "USERNAME": username,
                    "SRP_A": srp_a,
                    "SECRET_HASH": self._calculate_secret_hash(username) if self.client_secret else None
                }
            )
            
            logger.debug("Cognito SRP auth initiated", username=username)
            return response
            
        except Exception as e:
            logger.error("Cognito SRP auth failed", username=username, error=str(e))
            raise
    
    async def respond_to_srp_challenge(
        self,
        username: str,
        challenge_name: str,
        session: str,
        challenge_responses: Dict[str, str]
    ) -> Dict[str, Any]:
        """Respond to SRP challenge"""
        try:
            if self.client_secret:
                challenge_responses["SECRET_HASH"] = self._calculate_secret_hash(username)
            
            response = self.client.respond_to_auth_challenge(
                ClientId=self.client_id,
                ChallengeName=challenge_name,
                Session=session,
                ChallengeResponses=challenge_responses
            )
            
            logger.debug("Cognito SRP challenge response", username=username, challenge=challenge_name)
            return response
            
        except Exception as e:
            logger.error("Cognito SRP challenge failed", username=username, error=str(e))
            raise
    
    async def sign_up(
        self,
        username: str,
        password: str,
        email: str,
        given_name: Optional[str] = None,
        family_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sign up a new user"""
        try:
            user_attributes = [
                {"Name": "email", "Value": email}
            ]
            
            if given_name:
                user_attributes.append({"Name": "given_name", "Value": given_name})
            if family_name:
                user_attributes.append({"Name": "family_name", "Value": family_name})
            
            response = self.client.sign_up(
                ClientId=self.client_id,
                Username=username,
                Password=password,
                UserAttributes=user_attributes,
                SecretHash=self._calculate_secret_hash(username) if self.client_secret else None
            )
            
            logger.info("User signed up", username=username, email=email)
            return response
            
        except Exception as e:
            logger.error("Cognito signup failed", username=username, email=email, error=str(e))
            raise
    
    async def confirm_sign_up(
        self,
        username: str,
        confirmation_code: str
    ) -> Dict[str, Any]:
        """Confirm user sign up with verification code"""
        try:
            response = self.client.confirm_sign_up(
                ClientId=self.client_id,
                Username=username,
                ConfirmationCode=confirmation_code,
                SecretHash=self._calculate_secret_hash(username) if self.client_secret else None
            )
            
            logger.info("User signup confirmed", username=username)
            return response
            
        except Exception as e:
            logger.error("Cognito signup confirmation failed", username=username, error=str(e))
            raise
    
    async def resend_confirmation_code(
        self,
        username: str
    ) -> Dict[str, Any]:
        """Resend confirmation code"""
        try:
            response = self.client.resend_confirmation_code(
                ClientId=self.client_id,
                Username=username,
                SecretHash=self._calculate_secret_hash(username) if self.client_secret else None
            )
            
            logger.info("Confirmation code resent", username=username)
            return response
            
        except Exception as e:
            logger.error("Resend confirmation failed", username=username, error=str(e))
            raise
    
    async def forgot_password(
        self,
        username: str
    ) -> Dict[str, Any]:
        """Initiate forgot password flow"""
        try:
            response = self.client.forgot_password(
                ClientId=self.client_id,
                Username=username,
                SecretHash=self._calculate_secret_hash(username) if self.client_secret else None
            )
            
            logger.info("Forgot password initiated", username=username)
            return response
            
        except Exception as e:
            logger.error("Forgot password failed", username=username, error=str(e))
            raise
    
    async def confirm_forgot_password(
        self,
        username: str,
        confirmation_code: str,
        new_password: str
    ) -> Dict[str, Any]:
        """Confirm forgot password with new password"""
        try:
            response = self.client.confirm_forgot_password(
                ClientId=self.client_id,
                Username=username,
                ConfirmationCode=confirmation_code,
                Password=new_password,
                SecretHash=self._calculate_secret_hash(username) if self.client_secret else None
            )
            
            logger.info("Password reset confirmed", username=username)
            return response
            
        except Exception as e:
            logger.error("Password reset confirmation failed", username=username, error=str(e))
            raise
    
    async def refresh_token(
        self,
        refresh_token: str
    ) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={
                    "REFRESH_TOKEN": refresh_token
                }
            )
            
            logger.debug("Token refreshed")
            return response
            
        except Exception as e:
            logger.error("Token refresh failed", error=str(e))
            raise
    
    async def get_user(
        self,
        access_token: str
    ) -> Dict[str, Any]:
        """Get user information using access token"""
        try:
            response = self.client.get_user(
                AccessToken=access_token
            )
            
            logger.debug("User info retrieved")
            return response
            
        except Exception as e:
            logger.error("Get user failed", error=str(e))
            raise
    
    async def admin_get_user(
        self,
        username: str
    ) -> Dict[str, Any]:
        """Get user information using admin privileges"""
        try:
            response = self.client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            
            logger.debug("Admin user info retrieved", username=username)
            return response
            
        except Exception as e:
            logger.error("Admin get user failed", username=username, error=str(e))
            raise
    
    async def global_sign_out(
        self,
        access_token: str
    ) -> None:
        """Sign out user from all devices"""
        try:
            self.client.global_sign_out(
                AccessToken=access_token
            )
            
            logger.info("User signed out globally")
            
        except Exception as e:
            logger.error("Global sign out failed", error=str(e))
            raise
    
    async def get_hosted_ui_url(
        self,
        redirect_uri: str,
        state: Optional[str] = None,
        identity_provider: Optional[str] = None
    ) -> str:
        """Get Cognito Hosted UI URL for social login"""
        # This would be constructed based on Cognito domain configuration
        # For now, return a placeholder
        domain = f"https://{self.user_pool_id}.auth.{self.region}.amazoncognito.com"
        url = f"{domain}/oauth2/authorize?client_id={self.client_id}&response_type=code&redirect_uri={redirect_uri}"
        
        if state:
            url += f"&state={state}"
        if identity_provider:
            url += f"&identity_provider={identity_provider}"
        
        return url
    
    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        # This would typically use the OAuth2 token endpoint
        # Implementation depends on Cognito Hosted UI configuration
        # For now, return a placeholder
        return {
            "access_token": "placeholder",
            "id_token": "placeholder", 
            "refresh_token": "placeholder",
            "token_type": "Bearer",
            "expires_in": 3600
        }
    
    def _calculate_secret_hash(self, username: str) -> str:
        """Calculate secret hash for Cognito client"""
        if not self.client_secret:
            return None
        
        import hmac
        import hashlib
        import base64
        
        message = username + self.client_id
        dig = hmac.new(
            self.client_secret.encode('utf-8'),
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        return base64.b64encode(dig).decode()