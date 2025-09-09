import uuid
from typing import Dict, Any, Optional
from ..ports.session_repository import SessionRepository, CipherSessionRepository
from ..ports.cognito_client import CognitoClient
from ..ports.jwt_signer import JWTSigner, CipherService
from ...domain.services.auth_service import AuthDomainService
from ...domain.entities.user import User
from ...domain.value_objects.tokens import CipherEnvelope
from ...domain.errors import (
    InvalidCredentialsError, 
    CipherSessionError, 
    InvalidSessionError,
    CognitoError
)
import structlog

logger = structlog.get_logger(__name__)


class LoginUserUseCase:
    """Use case for user login with password (encrypted or plain)"""
    
    def __init__(
        self,
        session_repository: SessionRepository,
        cipher_session_repository: CipherSessionRepository,
        cognito_client: CognitoClient,
        jwt_signer: JWTSigner,
        cipher_service: CipherService,
        jwt_issuer: str,
        jwt_audience: str,
        access_token_ttl: int = 900,
        session_ttl: int = 1800
    ):
        self.session_repository = session_repository
        self.cipher_session_repository = cipher_session_repository
        self.cognito_client = cognito_client
        self.jwt_signer = jwt_signer
        self.cipher_service = cipher_service
        self.jwt_issuer = jwt_issuer
        self.jwt_audience = jwt_audience
        self.access_token_ttl = access_token_ttl
        self.session_ttl = session_ttl
    
    async def execute(
        self,
        username: str,
        password: Optional[str] = None,
        cipher_envelope: Optional[CipherEnvelope] = None,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Login user with password or cipher envelope
        
        Args:
            username: User's username or email
            password: Plain text password (fallback)
            cipher_envelope: Encrypted password envelope from client
            device_info: Device information
            ip_address: Client IP address  
            user_agent: Client user agent
            
        Returns:
            Dictionary with access_token and sid cookie value
        """
        try:
            # Decrypt password if cipher envelope provided
            if cipher_envelope:
                password = await self._decrypt_password(cipher_envelope)
            
            if not password:
                raise InvalidCredentialsError("Password is required")
            
            logger.info("Attempting user login", username=username)
            
            # Try SRP authentication first, fallback to password auth
            auth_result = await self._authenticate_with_cognito(username, password)
            
            # Get user information
            user = await self._get_user_from_cognito(auth_result)
            
            # Create session
            session_id = str(uuid.uuid4())
            session = AuthDomainService.create_session(
                sid=session_id,
                user=user,
                refresh_token=auth_result.get("RefreshToken", ""),
                ttl_seconds=self.session_ttl,
                device_info=device_info,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Save session
            await self.session_repository.save_session(session)
            
            # Create JWT claims
            scopes = AuthDomainService.get_default_user_scopes()
            claims = AuthDomainService.create_user_jwt_claims(
                user=user,
                session=session,
                issuer=self.jwt_issuer,
                audience=self.jwt_audience,
                ttl_seconds=self.access_token_ttl,
                jti=str(uuid.uuid4()),
                scopes=scopes
            )
            
            # Sign JWT
            access_token = await self.jwt_signer.sign_jwt(claims)
            
            logger.info("User login successful", username=username, user_id=user.id)
            
            return {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": self.access_token_ttl,
                "sid": session_id  # For httpOnly cookie
            }
            
        except Exception as e:
            logger.error("User login failed", username=username, error=str(e))
            if isinstance(e, (InvalidCredentialsError, CipherSessionError, InvalidSessionError)):
                raise
            raise CognitoError(f"Login failed: {e}")
    
    async def _decrypt_password(self, cipher_envelope: CipherEnvelope) -> str:
        """Decrypt password from cipher envelope"""
        try:
            # Get cipher session
            cipher_session = await self.cipher_session_repository.get_cipher_session(cipher_envelope.sid)
            if not cipher_session or not cipher_session.is_valid():
                raise CipherSessionError("Invalid or expired cipher session")
            
            # Decrypt password
            password = await self.cipher_service.decrypt_password(
                private_key_pem=cipher_session.server_private_key_pem,
                client_public_key_jwk=cipher_envelope.client_public_key_jwk,
                sid=cipher_envelope.sid,
                nonce=cipher_envelope.nonce,
                ciphertext=cipher_envelope.password_enc
            )
            
            # Clean up cipher session
            await self.cipher_session_repository.delete_cipher_session(cipher_envelope.sid)
            
            return password
            
        except Exception as e:
            logger.error("Password decryption failed", sid=cipher_envelope.sid, error=str(e))
            raise CipherSessionError(f"Failed to decrypt password: {e}")
    
    async def _authenticate_with_cognito(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate with Cognito using SRP or password auth"""
        try:
            # Try password auth first for simplicity
            # In production, implement SRP flow
            result = await self.cognito_client.initiate_auth(
                username=username,
                password=password,
                auth_flow="USER_PASSWORD_AUTH"
            )
            
            return result.get("AuthenticationResult", {})
            
        except Exception as e:
            logger.error("Cognito authentication failed", username=username, error=str(e))
            raise InvalidCredentialsError("Invalid username or password")
    
    async def _get_user_from_cognito(self, auth_result: Dict[str, Any]) -> User:
        """Get user information from Cognito"""
        try:
            access_token = auth_result.get("AccessToken")
            if not access_token:
                raise CognitoError("No access token in auth result")
            
            user_info = await self.cognito_client.get_user(access_token)
            
            # Map Cognito user to domain User
            attributes = {attr["Name"]: attr["Value"] for attr in user_info.get("UserAttributes", [])}
            
            return User(
                id=str(uuid.uuid4()),  # Generate internal user ID
                cognito_sub=attributes.get("sub", ""),
                email=attributes.get("email", ""),
                email_verified=attributes.get("email_verified", "false") == "true",
                phone_number=attributes.get("phone_number"),
                phone_verified=attributes.get("phone_number_verified", "false") == "true",
                given_name=attributes.get("given_name"),
                family_name=attributes.get("family_name"),
                preferred_username=attributes.get("preferred_username"),
                picture=attributes.get("picture"),
                locale=attributes.get("locale"),
                zoneinfo=attributes.get("zoneinfo"),
                user_status=user_info.get("UserStatus", "CONFIRMED"),
                enabled=user_info.get("Enabled", True)
            )
            
        except Exception as e:
            logger.error("Failed to get user from Cognito", error=str(e))
            raise CognitoError(f"Failed to get user information: {e}")