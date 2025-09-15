import structlog

from application.ports.cognito_client import CognitoClient
from application.ports.session_repository import SessionRepository
from domain.responses import ConfirmForgotPasswordResponse, ForgotPasswordResponse
from domain.services.validation_service import ValidationService

logger = structlog.get_logger(__name__)


class ForgotPasswordUseCase:
    """Use case for initiating forgot password flow"""

    def __init__(
        self,
        cognito_client: CognitoClient,
        session_repository: SessionRepository,
    ):
        self.cognito_client = cognito_client
        self.session_repository = session_repository

    async def execute(self, username: str) -> ForgotPasswordResponse:
        """
        Initiate forgot password flow

        Args:
            username: Username (email) for password reset

        Returns:
            Dict with reset status
        """
        try:
            # Validate input
            if not username:
                from domain.errors import ValidationError

                raise ValidationError("Username is required")

            logger.info("Initiating forgot password flow", username=username)

            # Initiate forgot password with Cognito
            response = await self.cognito_client.forgot_password(username)

            # Extract delivery information if available
            code_delivery = response.get("CodeDeliveryDetails", {})
            delivery_medium = code_delivery.get("DeliveryMedium", "EMAIL")
            destination = code_delivery.get("Destination", "")

            logger.info("Forgot password initiated", username=username, delivery_medium=delivery_medium)

            return ForgotPasswordResponse(
                message="Password reset code sent successfully",
                delivery_medium=delivery_medium,
                destination=destination,
            )

        except Exception as e:
            logger.error("Forgot password failed", username=username, error=str(e))

            # Handle specific Cognito errors
            error_message = str(e)
            if "UserNotFoundException" in error_message:
                # For security, don't reveal if user exists or not
                # Return success message anyway
                return ForgotPasswordResponse(
                    message="If the email exists, a password reset code has been sent",
                    delivery_medium="EMAIL",
                    destination="",
                )
            elif "LimitExceededException" in error_message:
                from domain.errors import ValidationError

                raise ValidationError("Too many password reset attempts. Please try again later.") from e
            else:
                raise


class ConfirmForgotPasswordUseCase:
    """Use case for confirming forgot password with new password"""

    def __init__(
        self,
        cognito_client: CognitoClient,
        session_repository: SessionRepository,
    ):
        self.cognito_client = cognito_client
        self.session_repository = session_repository

    async def execute(self, username: str, confirmation_code: str, new_password: str) -> ConfirmForgotPasswordResponse:
        """
        Confirm forgot password with new password

        Args:
            username: Username (email)
            confirmation_code: Verification code from email/SMS
            new_password: New password

        Returns:
            Dict with confirmation status
        """
        try:
            # Validate inputs
            if not username:
                from domain.errors import ValidationError

                raise ValidationError("Username is required")
            ValidationService.validate_confirmation_code(confirmation_code)
            ValidationService.validate_password(new_password)

            logger.info("Confirming forgot password", username=username)

            # Confirm forgot password with Cognito
            await self.cognito_client.confirm_forgot_password(
                username=username,
                confirmation_code=confirmation_code,
                new_password=new_password,
            )

            # Invalidate all existing sessions for security
            # User should log in again after password reset
            await self._invalidate_user_sessions(username)

            logger.info("Forgot password confirmed", username=username)

            return ConfirmForgotPasswordResponse(
                success=True,
                message="Password reset successfully. Please log in with your new password.",
            )

        except Exception as e:
            logger.error("Confirm forgot password failed", username=username, error=str(e))

            # Handle specific Cognito errors
            error_message = str(e)
            if "CodeMismatchException" in error_message:
                from domain.errors import ValidationError

                raise ValidationError("Invalid confirmation code") from e
            elif "ExpiredCodeException" in error_message:
                from domain.errors import ValidationError

                raise ValidationError("Confirmation code has expired") from e
            elif "InvalidPasswordException" in error_message:
                from domain.errors import ValidationError

                raise ValidationError("Password does not meet requirements") from e
            elif "UserNotFoundException" in error_message:
                from domain.errors import ValidationError

                raise ValidationError("User not found") from e
            else:
                raise

    def _validate_password(self, password: str) -> None:
        """Validate password meets basic requirements"""
        from domain.errors import ValidationError

        if not password:
            raise ValidationError("Password is required")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        if len(password) > 128:
            raise ValidationError("Password must be less than 128 characters")

    async def _invalidate_user_sessions(self, username: str) -> None:
        """Invalidate all sessions for a user after password reset"""
        try:
            # Try to get user's provider_sub to find sessions
            # This might fail if user doesn't exist in our system yet
            sessions = await self.session_repository.get_sessions_by_username(username)
            for session in sessions:
                await self.session_repository.invalidate_session(session.sid)

            if sessions:
                logger.info(
                    "User sessions invalidated after password reset", username=username, session_count=len(sessions)
                )

        except Exception as e:
            logger.warning("Failed to invalidate user sessions after password reset", username=username, error=str(e))
            # Don't raise - password reset can still succeed
