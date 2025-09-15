"""
Mock Cognito client for development purposes.
This simulates AWS Cognito behavior without requiring actual AWS resources.
DO NOT USE IN PRODUCTION!
"""

import hashlib
import uuid
from datetime import datetime, timedelta

import structlog

from application.ports.cognito_client import CognitoClient
from domain.entities.provider_entities import (
    AuthenticationChallenge,
    AuthenticationResult,
    CodeDeliveryDetails,
    ConfirmationResult,
    PasswordResetConfirmation,
    PasswordResetRequest,
    ResendCodeResult,
    TokenRefreshResult,
    TokenSet,
    UserRegistration,
)
from domain.entities.user import User

logger = structlog.get_logger(__name__)

# In-memory store for development users
DEV_USERS = {}
DEV_SESSIONS = {}
DEV_CONFIRMATION_CODES = {}


class MockCognitoClientAdapter(CognitoClient):
    """Mock Cognito client for development"""

    def __init__(self, user_pool_id: str, client_id: str, client_secret: str, region: str = "us-east-1"):
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.region = region

        logger.info(
            "Mock Cognito client initialized for development",
            client_id=client_id[:8] + "***",
            user_pool_id=user_pool_id[:15] + "***" if len(user_pool_id) > 15 else user_pool_id,
            region=region,
        )

    async def old_sign_up(
        self,
        username: str,
        password: str,
        given_name: str | None = None,
        family_name: str | None = None,
        phone_number: str | None = None,
    ) -> UserRegistration:
        """Mock user signup"""
        logger.info("Mock signup started", username=username)

        # Check if user already exists
        if username in DEV_USERS:
            raise Exception("User already exists")

        # Generate a mock user_sub
        user_sub = f"dev-user-{uuid.uuid4()}"

        # Hash password (simple hash for dev)
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Store user
        DEV_USERS[username] = {
            "user_sub": user_sub,
            "email": username,
            "password_hash": password_hash,
            "given_name": given_name,
            "family_name": family_name,
            "phone_number": phone_number,
            "email_verified": False,
            "created_at": datetime.utcnow(),
            "status": "UNCONFIRMED",
        }

        # Generate confirmation code
        confirmation_code = "123456"  # Fixed code for dev
        DEV_CONFIRMATION_CODES[username] = confirmation_code

        logger.info("Mock user created", username=username, user_sub=user_sub)

        return UserRegistration(
            user_sub=user_sub,
            user_confirmed=False,
            code_delivery_details=CodeDeliveryDetails(
                delivery_medium="EMAIL", destination=username, attribute_name="email"
            ),
        )

    async def confirm_sign_up(self, username: str, confirmation_code: str) -> ConfirmationResult:
        """Mock signup confirmation"""
        logger.info("Mock signup confirmation", username=username)

        if username not in DEV_USERS:
            raise Exception("User not found")

        if DEV_CONFIRMATION_CODES.get(username) != confirmation_code:
            raise Exception("Invalid confirmation code")

        # Mark as confirmed
        DEV_USERS[username]["email_verified"] = True
        DEV_USERS[username]["status"] = "CONFIRMED"

        # Clean up confirmation code
        if username in DEV_CONFIRMATION_CODES:
            del DEV_CONFIRMATION_CODES[username]

        logger.info("Mock user confirmed", username=username)

        return ConfirmationResult(success=True)

    async def resend_confirmation_code(self, username: str) -> ResendCodeResult:
        """Mock resend confirmation code"""
        logger.info("Mock resend confirmation code", username=username)

        if username not in DEV_USERS:
            raise Exception("User not found")

        # Set the confirmation code again
        DEV_CONFIRMATION_CODES[username] = "123456"

        return ResendCodeResult(
            code_delivery_details=CodeDeliveryDetails(
                delivery_medium="EMAIL", destination=username, attribute_name="email"
            )
        )

    async def authenticate(
        self,
        username: str,
        password: str,
        device_info: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthenticationResult:
        """Mock authentication"""
        logger.info("Mock authentication", username=username)

        if username not in DEV_USERS:
            raise Exception("User not found")

        user = DEV_USERS[username]
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        if user["password_hash"] != password_hash:
            raise Exception("Invalid password")

        if user["status"] != "CONFIRMED":
            raise Exception("User not confirmed")

        # Generate mock tokens
        access_token = f"mock-access-{uuid.uuid4()}"
        refresh_token = f"mock-refresh-{uuid.uuid4()}"
        id_token = f"mock-id-{uuid.uuid4()}"

        # Store session
        session_id = str(uuid.uuid4())
        DEV_SESSIONS[session_id] = {
            "username": username,
            "user_sub": user["user_sub"],
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "created_at": datetime.utcnow(),
        }

        logger.info("Mock authentication successful", username=username, user_sub=user["user_sub"])

        return AuthenticationResult(
            access_token=access_token,
            refresh_token=refresh_token,
            id_token=id_token,
            token_type="Bearer",
            expires_in=3600,
        )

    async def old_refresh_token(self, refresh_token: str) -> TokenSet:
        """Mock token refresh"""
        logger.info("Mock token refresh")

        # Find session by refresh token
        session = None
        for _sid, sess in DEV_SESSIONS.items():
            if sess["refresh_token"] == refresh_token:
                session = sess
                break

        if not session:
            raise Exception("Invalid refresh token")

        if session["expires_at"] < datetime.utcnow():
            raise Exception("Refresh token expired")

        # Generate new tokens
        new_access_token = f"mock-access-{uuid.uuid4()}"
        new_refresh_token = f"mock-refresh-{uuid.uuid4()}"

        # Update session
        session["access_token"] = new_access_token
        session["refresh_token"] = new_refresh_token
        session["expires_at"] = datetime.utcnow() + timedelta(hours=1)

        logger.info("Mock token refreshed", user_sub=session["user_sub"])

        return TokenSet(
            access_token=new_access_token, refresh_token=new_refresh_token, token_type="Bearer", expires_in=3600
        )

    async def old_global_sign_out(self, access_token: str) -> dict:
        """Mock global sign out"""
        logger.info("Mock global sign out")

        # Find and remove session by access token
        to_remove = []
        for sid, session in DEV_SESSIONS.items():
            if session["access_token"] == access_token:
                to_remove.append(sid)

        for sid in to_remove:
            del DEV_SESSIONS[sid]

        return {"message": "Global sign out successful"}

    async def forgot_password(self, username: str) -> PasswordResetRequest:
        """Mock forgot password"""
        logger.info("Mock forgot password", username=username)

        if username not in DEV_USERS:
            raise Exception("User not found")

        # Generate mock confirmation code
        DEV_CONFIRMATION_CODES[f"reset_{username}"] = "654321"

        return PasswordResetRequest(
            code_delivery_details=CodeDeliveryDetails(
                delivery_medium="EMAIL", destination=username, attribute_name="email"
            )
        )

    async def confirm_forgot_password(
        self, username: str, confirmation_code: str, new_password: str
    ) -> PasswordResetConfirmation:
        """Mock confirm forgot password"""
        logger.info("Mock confirm forgot password", username=username)

        if username not in DEV_USERS:
            raise Exception("User not found")

        reset_key = f"reset_{username}"
        if DEV_CONFIRMATION_CODES.get(reset_key) != confirmation_code:
            raise Exception("Invalid confirmation code")

        # Update password
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        DEV_USERS[username]["password_hash"] = password_hash

        # Clean up reset code
        if reset_key in DEV_CONFIRMATION_CODES:
            del DEV_CONFIRMATION_CODES[reset_key]

        logger.info("Mock password reset successful", username=username)

        return PasswordResetConfirmation(success=True)

    async def old_exchange_code_for_tokens(self, authorization_code: str, redirect_uri: str) -> AuthenticationResult:
        """Mock OAuth code exchange"""
        logger.info("Mock OAuth code exchange")

        # Mock OAuth flow - create a demo user
        mock_email = "oauth.user@example.com"
        mock_sub = f"oauth-{uuid.uuid4()}"

        # Create or get OAuth user
        if mock_email not in DEV_USERS:
            DEV_USERS[mock_email] = {
                "user_sub": mock_sub,
                "email": mock_email,
                "password_hash": None,  # OAuth users don't have passwords
                "given_name": "OAuth",
                "family_name": "User",
                "phone_number": None,
                "email_verified": True,
                "created_at": datetime.utcnow(),
                "status": "CONFIRMED",
            }

        user = DEV_USERS[mock_email]

        # Generate tokens
        access_token = f"mock-oauth-access-{uuid.uuid4()}"
        refresh_token = f"mock-oauth-refresh-{uuid.uuid4()}"
        id_token = f"mock-oauth-id-{uuid.uuid4()}"

        logger.info("Mock OAuth authentication successful", email=mock_email, user_sub=user["user_sub"])

        return AuthenticationResult(
            access_token=access_token,
            refresh_token=refresh_token,
            id_token=id_token,
            token_type="Bearer",
            expires_in=3600,
        )

    # Required abstract methods from CognitoClient

    async def initiate_auth(
        self, username: str, password: str, auth_flow: str = "USER_PASSWORD_AUTH"
    ) -> AuthenticationChallenge:
        """Mock initiate auth - delegates to authenticate"""
        try:
            auth_result = await self.authenticate(username, password)
            return AuthenticationChallenge(authentication_result=auth_result)
        except Exception as e:
            logger.error("Mock initiate auth failed", username=username, error=str(e))
            raise

    async def initiate_srp_auth(self, username: str, srp_a: str) -> AuthenticationChallenge:
        """Mock SRP auth - not implemented for simplicity"""
        logger.warning("SRP auth not implemented in mock")
        raise NotImplementedError("SRP auth not implemented in mock client")

    async def respond_to_srp_challenge(
        self,
        username: str,
        challenge_name: str,
        session: str,
        challenge_responses: dict[str, str],
    ) -> AuthenticationChallenge:
        """Mock SRP challenge response - not implemented"""
        logger.warning("SRP challenge not implemented in mock")
        raise NotImplementedError("SRP challenge not implemented in mock client")

    # Note: The original sign_up method signature is different, so we need to rename it
    async def _original_sign_up(
        self,
        username: str,
        password: str,
        given_name: str | None = None,
        family_name: str | None = None,
        phone_number: str | None = None,
    ) -> UserRegistration:
        """Original signup implementation"""
        logger.info("Mock signup started", username=username)

        # Check if user already exists
        if username in DEV_USERS:
            raise Exception("User already exists")

        # Generate a mock user_sub
        user_sub = f"dev-user-{uuid.uuid4()}"

        # Hash password (simple hash for dev)
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Store user
        DEV_USERS[username] = {
            "user_sub": user_sub,
            "email": username,
            "password_hash": password_hash,
            "given_name": given_name,
            "family_name": family_name,
            "phone_number": phone_number,
            "email_verified": False,
            "created_at": datetime.utcnow(),
            "status": "UNCONFIRMED",
        }

        # Generate confirmation code
        confirmation_code = "123456"  # Fixed code for dev
        DEV_CONFIRMATION_CODES[username] = confirmation_code

        logger.info("Mock user created", username=username, user_sub=user_sub)

        return UserRegistration(
            user_sub=user_sub,
            user_confirmed=False,
            code_delivery_details=CodeDeliveryDetails(
                delivery_medium="EMAIL", destination=username, attribute_name="email"
            ),
        )

    async def sign_up(
        self,
        username: str,
        password: str,
        email: str,
        given_name: str | None = None,
        family_name: str | None = None,
    ) -> UserRegistration:
        """Mock signup - interface method"""
        return await self._original_sign_up(username, password, given_name, family_name)

    async def refresh_token(self, refresh_token: str) -> TokenRefreshResult:
        """Mock token refresh"""
        token_set = await self.old_refresh_token(refresh_token)

        # Create a mock AuthenticationResult from TokenSet
        auth_result = AuthenticationResult(
            access_token=token_set.access_token,
            refresh_token=token_set.refresh_token,
            id_token="mock-id-token",  # TokenSet doesn't have id_token
            token_type=token_set.token_type,
            expires_in=token_set.expires_in,
        )

        return TokenRefreshResult(authentication_result=auth_result)

    async def get_user(self, access_token: str) -> User:
        """Get user by access token"""
        # Find user by access token
        for session in DEV_SESSIONS.values():
            if session["access_token"] == access_token:
                username = session["username"]
                if username in DEV_USERS:
                    user_data = DEV_USERS[username]
                    return User(
                        id=user_data["user_sub"],
                        provider_sub=user_data["user_sub"],
                        email=user_data["email"],
                        email_verified=user_data["email_verified"],
                        given_name=user_data.get("given_name"),
                        family_name=user_data.get("family_name"),
                        phone_number=user_data.get("phone_number"),
                        enabled=user_data["status"] == "CONFIRMED",
                        user_status=user_data["status"],
                        created_at=user_data["created_at"],
                        updated_at=user_data["created_at"],
                    )

        logger.warning("User not found for access token")
        raise Exception("User not found")

    async def admin_get_user(self, username: str) -> User:
        """Get user by username (admin operation)"""
        if username not in DEV_USERS:
            raise Exception("User not found")

        user_data = DEV_USERS[username]
        return User(
            id=user_data["user_sub"],
            provider_sub=user_data["user_sub"],
            email=user_data["email"],
            email_verified=user_data["email_verified"],
            given_name=user_data.get("given_name"),
            family_name=user_data.get("family_name"),
            phone_number=user_data.get("phone_number"),
            enabled=user_data["status"] == "CONFIRMED",
            user_status=user_data["status"],
            created_at=user_data["created_at"],
            updated_at=user_data["created_at"],
        )

    async def global_sign_out(self, access_token: str) -> None:
        """Global sign out - delegates to existing method"""
        await self.old_global_sign_out(access_token)

    async def get_hosted_ui_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        identity_provider: str | None = None,
    ) -> str:
        """Mock hosted UI URL"""
        base_url = "http://localhost:8083/auth/mock-hosted-ui"
        params = [f"redirect_uri={redirect_uri}"]
        if state:
            params.append(f"state={state}")
        if identity_provider:
            params.append(f"identity_provider={identity_provider}")

        return f"{base_url}?{'&'.join(params)}"

    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> TokenSet:
        """Mock code exchange - delegates to existing method"""
        auth_result = await self.old_exchange_code_for_tokens(code, redirect_uri)

        return TokenSet(
            access_token=auth_result.access_token,
            refresh_token=auth_result.refresh_token,
            token_type=auth_result.token_type,
            expires_in=auth_result.expires_in,
        )
