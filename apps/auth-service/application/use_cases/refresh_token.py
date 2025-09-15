from datetime import datetime, timedelta

import structlog

from application.ports.cognito_client import CognitoClient
from application.ports.jwt_signer import JWTSigner
from application.ports.session_repository import SessionRepository
from domain.responses import RefreshTokenResponse
from domain.services.auth_service import AuthDomainService

logger = structlog.get_logger(__name__)


class RefreshTokenUseCase:
    """Use case for refreshing access tokens using session or refresh token"""

    def __init__(
        self,
        session_repository: SessionRepository,
        cognito_client: CognitoClient,
        jwt_signer: JWTSigner,
        jwt_issuer: str,
        jwt_audience: str,
        access_token_ttl: int,
    ):
        self.session_repository = session_repository
        self.cognito_client = cognito_client
        self.jwt_signer = jwt_signer
        self.jwt_issuer = jwt_issuer
        self.jwt_audience = jwt_audience
        self.access_token_ttl = access_token_ttl

    async def execute_with_session(self, sid: str) -> RefreshTokenResponse:
        """
        Refresh access token using session ID

        Args:
            sid: Session ID from cookie

        Returns:
            Dict containing new access token

        Raises:
            InvalidSessionError: If session is invalid or expired
        """
        try:
            logger.info("Refreshing token with session", sid=sid)

            # Get session
            session = await self.session_repository.get_session(sid)
            if not session:
                from domain.errors import InvalidSessionError

                raise InvalidSessionError("Session not found")

            # Validate session
            if not AuthDomainService.validate_session(session):
                from domain.errors import SessionExpiredError

                raise SessionExpiredError("Session has expired")

            # Check if session should be refreshed with Cognito
            if AuthDomainService.should_refresh_session(session):
                await self._refresh_session_with_cognito(session)

            # Generate new access token
            scopes = AuthDomainService.get_default_user_scopes()

            # Create JWT claims (simplified - would need user data in real implementation)
            import uuid

            jwt_claims = {
                "sub": session.user_id,
                "sid": session.sid,
                "sidv": session.version,
                "scope": " ".join(scopes),
                "jti": str(uuid.uuid4()),
                "token_use": "access",
                "ver": 1,
            }

            access_token = await self.jwt_signer.sign_jwt(jwt_claims)

            # Update session last accessed time
            session.last_accessed = datetime.utcnow()
            await self.session_repository.update_session(session)

            logger.info("Token refreshed successfully", sid=sid, user_id=session.user_id)

            return RefreshTokenResponse(
                access_token=access_token,
                token_type="Bearer",
                expires_in=self.access_token_ttl,
            )

        except Exception as e:
            logger.error("Token refresh failed", sid=sid, error=str(e))
            raise

    async def execute_with_refresh_token(self, refresh_token: str) -> RefreshTokenResponse:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Cognito refresh token

        Returns:
            Dict containing new access token and potentially new refresh token
        """
        try:
            logger.info("Refreshing token with refresh token")

            # Refresh with Cognito
            cognito_response = await self.cognito_client.refresh_token(refresh_token)

            auth_result = cognito_response.get("AuthenticationResult", {})
            new_access_token = auth_result.get("AccessToken")
            new_refresh_token = auth_result.get("RefreshToken", refresh_token)

            if not new_access_token:
                from domain.errors import InvalidTokenError

                raise InvalidTokenError("Failed to refresh token with Cognito")

            # Get user info from new access token
            user_info = await self.cognito_client.get_user(new_access_token)

            # Find and update session if it exists
            provider_sub = user_info.provider_sub
            if provider_sub:
                sessions = await self.session_repository.get_sessions_by_provider_sub(provider_sub)
                for session in sessions:
                    if session.refresh_token == refresh_token:
                        session.refresh_token = new_refresh_token
                        session.last_accessed = datetime.utcnow()
                        await self.session_repository.update_session(session)
                        break

            logger.info("Token refreshed with Cognito", provider_sub=provider_sub)

            return RefreshTokenResponse(
                access_token=new_access_token,
                token_type="Bearer",
                expires_in=auth_result.get("ExpiresIn", self.access_token_ttl),
            )

        except Exception as e:
            logger.error("Token refresh with refresh token failed", error=str(e))
            raise

    async def _refresh_session_with_cognito(self, session) -> None:
        """Refresh session using Cognito refresh token"""
        try:
            if not session.refresh_token:
                return

            cognito_response = await self.cognito_client.refresh_token(session.refresh_token)
            auth_result = cognito_response.get("AuthenticationResult", {})

            new_refresh_token = auth_result.get("RefreshToken")
            if new_refresh_token:
                session.refresh_token = new_refresh_token
                session.expires_at = datetime.utcnow() + timedelta(seconds=1800)  # Extend session
                await self.session_repository.update_session(session)

        except Exception as e:
            logger.warning("Failed to refresh session with Cognito", sid=session.sid, error=str(e))
            # Don't raise - we can still use the existing session
