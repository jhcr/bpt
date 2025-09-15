import structlog

from application.ports.cognito_client import CognitoClient
from application.ports.session_repository import SessionRepository
from domain.responses import LogoutResponse

logger = structlog.get_logger(__name__)


class LogoutUserUseCase:
    """Use case for logging out users and invalidating sessions"""

    def __init__(
        self,
        session_repository: SessionRepository,
        cognito_client: CognitoClient,
    ):
        self.session_repository = session_repository
        self.cognito_client = cognito_client

    async def execute(
        self,
        sid: str | None = None,
        access_token: str | None = None,
        global_logout: bool = False,
    ) -> LogoutResponse:
        """
        Logout user by invalidating session and optionally signing out from Cognito

        Args:
            sid: Session ID to invalidate (from cookie)
            access_token: Access token for global logout
            global_logout: Whether to sign out from all devices via Cognito

        Returns:
            Dict with logout status
        """
        try:
            logger.info("Logging out user", sid=sid, global_logout=global_logout)

            sessions_terminated = 0
            global_logout_success = False

            # Invalidate session if provided
            if sid:
                session = await self.session_repository.get_session(sid)
                if session:
                    # Invalidate the specific session
                    await self.session_repository.invalidate_session(sid)
                    sessions_terminated = 1
                    logger.info("Session invalidated", sid=sid, user_id=session.user_id)

                    # For global logout, invalidate all user sessions
                    if global_logout and session.provider_sub:
                        all_sessions = await self._invalidate_all_user_sessions(session.provider_sub)
                        sessions_terminated = all_sessions

                        # Also sign out from Cognito if we have access token
                        if access_token:
                            try:
                                await self.cognito_client.global_sign_out(access_token)
                                global_logout_success = True
                                logger.info("Global logout completed", provider_sub=session.provider_sub)
                            except Exception as e:
                                logger.warning("Cognito global logout failed", error=str(e))
                                # Don't fail the whole logout if Cognito logout fails
                else:
                    logger.warning("Session not found for logout", sid=sid)

            # If only access token provided (no session), try global logout with Cognito
            elif access_token and global_logout:
                try:
                    # Get user info to find sessions
                    user_info = await self.cognito_client.get_user(access_token)
                    provider_sub = user_info.provider_sub

                    if provider_sub:
                        sessions_terminated = await self._invalidate_all_user_sessions(provider_sub)

                    await self.cognito_client.global_sign_out(access_token)
                    global_logout_success = True
                    logger.info("Global logout completed via access token", provider_sub=provider_sub)
                except Exception as e:
                    logger.error("Access token logout failed", error=str(e))
                    raise

            logger.info(
                "Logout completed", sessions_terminated=sessions_terminated, global_logout=global_logout_success
            )
            return LogoutResponse(
                success=True, message="Logged out successfully", sessions_terminated=sessions_terminated
            )

        except Exception as e:
            logger.error("Logout failed", sid=sid, error=str(e))
            raise

    async def _invalidate_all_user_sessions(self, provider_sub: str) -> int:
        """Invalidate all sessions for a user"""
        try:
            sessions = await self.session_repository.get_sessions_by_provider_sub(provider_sub)
            count = 0
            for session in sessions:
                try:
                    await self.session_repository.invalidate_session(session.sid)
                    count += 1
                except Exception as e:
                    logger.warning("Failed to invalidate session", sid=session.sid, error=str(e))

            logger.info("All user sessions invalidated", provider_sub=provider_sub, session_count=count)
            return count

        except Exception as e:
            logger.error("Failed to invalidate all user sessions", provider_sub=provider_sub, error=str(e))
            # Don't raise - partial logout is better than no logout
            return 0
