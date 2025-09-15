import structlog

from application.ports.cognito_client import CognitoClient
from domain.responses import RegisterUserResponse
from domain.services.validation_service import ValidationService

logger = structlog.get_logger(__name__)


class RegisterUserUseCase:
    """Use case for registering a new user"""

    def __init__(self, cognito_client: CognitoClient):
        self.cognito_client = cognito_client

    async def execute(
        self,
        email: str,
        password: str,
        given_name: str | None = None,
        family_name: str | None = None,
        phone_number: str | None = None,
    ) -> RegisterUserResponse:
        """
        Register a new user with Cognito

        Args:
            email: User's email address (used as username)
            password: User's password
            given_name: User's first name (optional)
            family_name: User's last name (optional)
            phone_number: User's phone number (optional)

        Returns:
            Dict containing registration result

        Raises:
            ValidationError: If input validation fails
            UserRegistrationError: If registration fails
        """
        try:
            logger.info("Starting user registration", email=email)

            # Validate inputs
            self._validate_registration_data(email, password, given_name, family_name, phone_number)

            # Use email as username for Cognito
            username = email

            # Register user with Cognito
            cognito_response = await self.cognito_client.sign_up(
                username=username,
                password=password,
                email=email,
                given_name=given_name,
                family_name=family_name,
            )

            logger.info("User registration successful", email=email, user_sub=cognito_response.user_sub)

            user_confirmed = cognito_response.user_confirmed
            code_delivery = cognito_response.code_delivery_details

            return RegisterUserResponse(
                user_sub=cognito_response.user_sub,
                confirmation_required=not user_confirmed,
                delivery_medium=code_delivery.delivery_medium if code_delivery else None,
                destination=code_delivery.destination if code_delivery else None,
            )

        except Exception as e:
            logger.error("User registration failed", email=email, error=str(e))

            # Handle specific Cognito errors
            from domain.errors import UserRegistrationError, ValidationError

            error_message = str(e)
            if "UsernameExistsException" in error_message:
                raise UserRegistrationError("User with this email already exists") from e
            elif "InvalidPasswordException" in error_message:
                raise ValidationError("Password does not meet requirements") from e
            elif "InvalidParameterException" in error_message:
                raise ValidationError("Invalid registration parameters") from e
            else:
                raise UserRegistrationError(f"Registration failed: {error_message}") from e

    def _validate_registration_data(
        self,
        email: str,
        password: str,
        given_name: str | None,
        family_name: str | None,
        phone_number: str | None = None,
    ) -> None:
        """Validate registration input data using domain validation service"""

        # Use domain validation service for comprehensive validation
        ValidationService.validate_email(email)
        ValidationService.validate_password(password)
        ValidationService.validate_name(given_name, "given_name")
        ValidationService.validate_name(family_name, "family_name")
        ValidationService.validate_phone_number(phone_number)
