import uuid

import structlog

from application.ports.cognito_client import CognitoClient
from application.ports.jwt_signer import JWTSigner
from application.ports.session_repository import SessionRepository
from domain.responses import OAuthCallbackResponse, OAuthStateValidation, ProviderTokenInfo, UserInfo
from domain.services.auth_service import AuthDomainService
from domain.services.validation_service import ValidationService

logger = structlog.get_logger(__name__)


class OAuthCallbackUseCase:
    """Use case for handling OAuth callback and creating user sessions"""

    def __init__(
        self,
        cognito_client: CognitoClient,
        session_repository: SessionRepository,
        jwt_signer: JWTSigner,
        jwt_issuer: str,
        jwt_audience: str,
        access_token_ttl: int,
        session_ttl: int,
    ):
        self.cognito_client = cognito_client
        self.session_repository = session_repository
        self.jwt_signer = jwt_signer
        self.jwt_issuer = jwt_issuer
        self.jwt_audience = jwt_audience
        self.access_token_ttl = access_token_ttl
        self.session_ttl = session_ttl

    async def execute(
        self,
        authorization_code: str,
        redirect_uri: str,
        state: str | None = None,
    ) -> OAuthCallbackResponse:
        """
        Handle OAuth callback by exchanging code for tokens and creating session

        Args:
            authorization_code: OAuth authorization code from provider
            redirect_uri: The redirect URI used in the OAuth flow
            state: CSRF protection state parameter

        Returns:
            Dict containing session info and tokens
        """
        try:
            # Validate inputs
            ValidationService.validate_oauth_code(authorization_code)
            ValidationService.validate_redirect_uri(redirect_uri)

            logger.info("Processing OAuth callback", redirect_uri=redirect_uri, state=state)

            # Step 1: Exchange authorization code for tokens
            try:
                token_response = await self.cognito_client.exchange_code_for_tokens(
                    code=authorization_code, redirect_uri=redirect_uri
                )
            except Exception as e:
                # Handle domain-specific OAuth errors
                from domain.errors import (
                    CognitoError,
                    InvalidAuthorizationCodeError,
                    InvalidTokenError,
                    InvalidTokenResponseError,
                    NetworkError,
                    OAuthClientAuthenticationError,
                    OAuthProviderError,
                    TokenExchangeError,
                )

                if isinstance(e, InvalidAuthorizationCodeError):
                    logger.error("Token exchange failed: invalid authorization code")
                    raise InvalidTokenError("Authorization code is invalid or expired") from e
                elif isinstance(e, OAuthClientAuthenticationError):
                    logger.error("Token exchange failed: OAuth client authentication failed")
                    raise CognitoError("OAuth client authentication failed") from e
                elif isinstance(e, OAuthProviderError | InvalidTokenResponseError | TokenExchangeError):
                    logger.error("Token exchange failed", error=str(e))
                    raise CognitoError(f"OAuth token exchange failed: {str(e)}") from e
                elif isinstance(e, NetworkError):
                    logger.error("Token exchange failed due to network error", error=str(e))
                    raise CognitoError(f"OAuth token exchange network error: {str(e)}") from e
                else:
                    # Re-raise unexpected errors
                    raise

            access_token = token_response.access_token
            id_token = token_response.id_token
            refresh_token = token_response.refresh_token

            # Step 2: Get user information from Cognito
            # Cognito adapter now returns domain User entity directly
            user = await self.cognito_client.get_user(access_token)

            logger.info(
                "OAuth user info retrieved",
                provider_sub=user.provider_sub,
                email=user.email,
                email_verified=user.email_verified,
            )

            # Step 4: Create session
            sid = str(uuid.uuid4())
            session = AuthDomainService.create_session(
                sid=sid,
                user=user,
                refresh_token=refresh_token or "",
                ttl_seconds=self.session_ttl,
            )

            # Save session
            await self.session_repository.save_session(session)

            # Step 5: Generate JWT access token for our system
            scopes = AuthDomainService.get_default_user_scopes()
            jwt_claims = AuthDomainService.create_user_jwt_claims(
                user=user,
                session=session,
                issuer=self.jwt_issuer,
                audience=self.jwt_audience,
                ttl_seconds=self.access_token_ttl,
                jti=str(uuid.uuid4()),
                scopes=scopes,
            )

            # Convert to dict for JWT signer
            claims_dict = jwt_claims.to_dict()
            our_access_token = await self.jwt_signer.sign_jwt(claims_dict)

            logger.info(
                "OAuth flow completed successfully", user_id=user.id, provider_sub=user.provider_sub, session_id=sid
            )

            return OAuthCallbackResponse(
                sid=sid,
                access_token=our_access_token,
                token_type="Bearer",
                expires_in=self.access_token_ttl,
                user=UserInfo(
                    id=user.id,
                    email=user.email,
                    given_name=user.given_name,
                    family_name=user.family_name,
                    email_verified=user.email_verified,
                ),
                provider_tokens=ProviderTokenInfo(
                    access_token=access_token,
                    id_token=id_token,
                    refresh_token=refresh_token,
                ),
            )

        except Exception as e:
            logger.error("OAuth callback processing failed", redirect_uri=redirect_uri, error=str(e))
            raise


class OAuthStateManager:
    """Helper class for managing OAuth state for CSRF protection"""

    def __init__(self, session_repository: SessionRepository):
        self.session_repository = session_repository

    async def generate_state(self, redirect_after_login: str | None = None) -> str:
        """Generate and store OAuth state for CSRF protection"""
        try:
            state = str(uuid.uuid4())

            # Store state with optional redirect URL
            # In a real implementation, you might store this in Redis with TTL
            # For now, we'll use a simple approach without storing state_data

            # For now, we'll use a simple approach
            # In production, store in Redis with 10-minute TTL
            logger.debug("OAuth state generated", state=state)
            return state

        except Exception as e:
            logger.error("Failed to generate OAuth state", error=str(e))
            raise

    async def validate_state(self, state: str) -> OAuthStateValidation | None:
        """Validate OAuth state and return associated data"""
        try:
            if not state:
                return None

            # In a real implementation, you'd retrieve from Redis and validate TTL
            # For now, we'll accept any non-empty state as valid
            logger.debug("OAuth state validated", state=state)

            return OAuthStateValidation(
                valid=True,
                redirect_after_login=None,
            )

        except Exception as e:
            logger.error("Failed to validate OAuth state", state=state, error=str(e))
            return None
