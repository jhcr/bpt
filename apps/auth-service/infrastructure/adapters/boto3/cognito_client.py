import boto3
import structlog

from application.ports.cognito_client import CognitoClient
from domain.entities.provider_entities import (
    AdminProviderUser,
    AuthenticationChallenge,
    AuthenticationResult,
    CodeDeliveryDetails,
    ConfirmationResult,
    PasswordResetConfirmation,
    PasswordResetRequest,
    ProviderUser,
    ResendCodeResult,
    TokenRefreshResult,
    TokenSet,
    UserAttributes,
    UserRegistration,
)
from domain.entities.user import User
from domain.errors import (
    InvalidAuthorizationCodeError,
    InvalidTokenResponseError,
    NetworkError,
    OAuthClientAuthenticationError,
    OAuthProviderError,
    TokenExchangeError,
)
from domain.services.user_mapper import UserMapper

logger = structlog.get_logger(__name__)


class CognitoClientAdapter(CognitoClient):
    """AWS Cognito client adapter using boto3"""

    def __init__(
        self,
        user_pool_id: str,
        client_id: str,
        client_secret: str,
        region: str = "us-east-1",
        endpoint_url: str = None,
    ):
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.region = region

        # Configure boto3 client with optional endpoint URL for localstack
        client_config = {"region_name": region}
        if endpoint_url:
            client_config["endpoint_url"] = endpoint_url
            # For localstack, we need dummy credentials
            client_config["aws_access_key_id"] = "test"
            client_config["aws_secret_access_key"] = "test"

        self.client = boto3.client("cognito-idp", **client_config)

        logger.info(
            "Cognito client initialized",
            user_pool_id=user_pool_id[:15] + "***" if len(user_pool_id) > 15 else user_pool_id,
            client_id=client_id[:8] + "***" if len(client_id) > 8 else client_id,
            region=region,
            endpoint_url=endpoint_url,
        )

    async def initiate_auth(
        self, username: str, password: str, auth_flow: str = "USER_PASSWORD_AUTH"
    ) -> AuthenticationChallenge:
        """Initiate authentication with Cognito"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow=auth_flow,
                AuthParameters={
                    "USERNAME": username,
                    "PASSWORD": password,
                    "SECRET_HASH": (self._calculate_secret_hash(username) if self.client_secret else None),
                },
            )

            logger.debug("Cognito auth initiated", username=username, auth_flow=auth_flow)

            # Convert raw Cognito response to typed response
            auth_result = response.get("AuthenticationResult")
            return AuthenticationChallenge(
                challenge_name=response.get("ChallengeName"),
                session=response.get("Session"),
                authentication_result=AuthenticationResult(
                    access_token=auth_result["AccessToken"],
                    expires_in=auth_result["ExpiresIn"],
                    token_type=auth_result["TokenType"],
                    refresh_token=auth_result.get("RefreshToken"),
                    id_token=auth_result.get("IdToken"),
                )
                if auth_result
                else None,
            )

        except Exception as e:
            logger.error("Cognito auth failed", username=username, error=str(e))
            raise

    async def initiate_srp_auth(self, username: str, srp_a: str) -> AuthenticationChallenge:
        """Initiate SRP authentication"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow="USER_SRP_AUTH",
                AuthParameters={
                    "USERNAME": username,
                    "SRP_A": srp_a,
                    "SECRET_HASH": (self._calculate_secret_hash(username) if self.client_secret else None),
                },
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
        challenge_responses: dict[str, str],
    ) -> AuthenticationChallenge:
        """Respond to SRP challenge"""
        try:
            if self.client_secret:
                challenge_responses["SECRET_HASH"] = self._calculate_secret_hash(username)

            response = self.client.respond_to_auth_challenge(
                ClientId=self.client_id,
                ChallengeName=challenge_name,
                Session=session,
                ChallengeResponses=challenge_responses,
            )

            logger.debug(
                "Cognito SRP challenge response",
                username=username,
                challenge=challenge_name,
            )
            return response

        except Exception as e:
            logger.error("Cognito SRP challenge failed", username=username, error=str(e))
            raise

    async def sign_up(
        self,
        username: str,
        password: str,
        email: str,
        given_name: str | None = None,
        family_name: str | None = None,
    ) -> UserRegistration:
        """Sign up a new user"""
        try:
            user_attributes = [{"Name": "email", "Value": email}]

            if given_name:
                user_attributes.append({"Name": "given_name", "Value": given_name})
            if family_name:
                user_attributes.append({"Name": "family_name", "Value": family_name})

            response = self.client.sign_up(
                ClientId=self.client_id,
                Username=username,
                Password=password,
                UserAttributes=user_attributes,
                SecretHash=(self._calculate_secret_hash(username) if self.client_secret else None),
            )

            logger.info("User signed up", username=username, email=email)

            # Parse response into typed format
            code_delivery = self._parse_code_delivery_details(response.get("CodeDeliveryDetails"))

            return UserRegistration(
                user_sub=response["UserSub"],
                user_confirmed=response.get("UserConfirmed", False),
                code_delivery_details=code_delivery,
            )

        except Exception as e:
            logger.error("Cognito signup failed", username=username, email=email, error=str(e))
            raise

    async def confirm_sign_up(self, username: str, confirmation_code: str) -> ConfirmationResult:
        """Confirm user sign up with verification code"""
        try:
            response = self.client.confirm_sign_up(
                ClientId=self.client_id,
                Username=username,
                ConfirmationCode=confirmation_code,
                SecretHash=(self._calculate_secret_hash(username) if self.client_secret else None),
            )

            logger.info("User signup confirmed", username=username)
            return response

        except Exception as e:
            logger.error("Cognito signup confirmation failed", username=username, error=str(e))
            raise

    async def resend_confirmation_code(self, username: str) -> ResendCodeResult:
        """Resend confirmation code"""
        try:
            response = self.client.resend_confirmation_code(
                ClientId=self.client_id,
                Username=username,
                SecretHash=(self._calculate_secret_hash(username) if self.client_secret else None),
            )

            logger.info("Confirmation code resent", username=username)
            return response

        except Exception as e:
            logger.error("Resend confirmation failed", username=username, error=str(e))
            raise

    async def forgot_password(self, username: str) -> PasswordResetRequest:
        """Initiate forgot password flow"""
        try:
            response = self.client.forgot_password(
                ClientId=self.client_id,
                Username=username,
                SecretHash=(self._calculate_secret_hash(username) if self.client_secret else None),
            )

            logger.info("Forgot password initiated", username=username)
            return response

        except Exception as e:
            logger.error("Forgot password failed", username=username, error=str(e))
            raise

    async def confirm_forgot_password(
        self, username: str, confirmation_code: str, new_password: str
    ) -> PasswordResetConfirmation:
        """Confirm forgot password with new password"""
        try:
            response = self.client.confirm_forgot_password(
                ClientId=self.client_id,
                Username=username,
                ConfirmationCode=confirmation_code,
                Password=new_password,
                SecretHash=(self._calculate_secret_hash(username) if self.client_secret else None),
            )

            logger.info("Password reset confirmed", username=username)
            return response

        except Exception as e:
            logger.error("Password reset confirmation failed", username=username, error=str(e))
            raise

    async def refresh_token(self, refresh_token: str) -> TokenRefreshResult:
        """Refresh access token using refresh token"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={"REFRESH_TOKEN": refresh_token},
            )

            logger.debug("Token refreshed")

            # Parse authentication result
            auth_result = response.get("AuthenticationResult", {})
            if not auth_result:
                raise Exception("No authentication result in refresh token response")

            return TokenRefreshResult(
                authentication_result=AuthenticationResult(
                    access_token=auth_result["AccessToken"],
                    expires_in=auth_result["ExpiresIn"],
                    token_type=auth_result["TokenType"],
                    refresh_token=auth_result.get("RefreshToken"),
                    id_token=auth_result.get("IdToken"),
                )
            )

        except Exception as e:
            logger.error("Token refresh failed", error=str(e))
            raise

    async def get_user(self, access_token: str) -> User:
        """Get user information using access token"""
        try:
            response = self.client.get_user(AccessToken=access_token)

            logger.debug("User info retrieved")

            # Parse user attributes
            user_attributes = self._parse_user_attributes(response.get("UserAttributes", []))

            # Create provider entity
            provider_user = ProviderUser(
                username=response["Username"],
                user_attributes=user_attributes,
                user_status=response.get("UserStatus"),
                enabled=response.get("Enabled", True),
            )

            # Convert to domain entity
            return UserMapper.provider_user_to_domain_user(provider_user)

        except Exception as e:
            logger.error("Get user failed", error=str(e))
            raise

    async def admin_get_user(self, username: str) -> User:
        """Get user information using admin privileges"""
        try:
            response = self.client.admin_get_user(UserPoolId=self.user_pool_id, Username=username)

            logger.debug("Admin user info retrieved", username=username)

            # Parse user attributes
            user_attributes = self._parse_user_attributes(response.get("UserAttributes", []))

            # Parse dates if present
            create_date = None
            modified_date = None
            if "UserCreateDate" in response:
                create_date = response["UserCreateDate"]
            if "UserLastModifiedDate" in response:
                modified_date = response["UserLastModifiedDate"]

            # Create admin provider entity
            admin_provider_user = AdminProviderUser(
                username=response["Username"],
                user_attributes=user_attributes,
                user_status=response["UserStatus"],
                enabled=response.get("Enabled", True),
                user_create_date=create_date,
                user_last_modified_date=modified_date,
            )

            # Convert to domain entity
            return UserMapper.admin_provider_user_to_domain_user(admin_provider_user)

        except Exception as e:
            logger.error("Admin get user failed", username=username, error=str(e))
            raise

    async def global_sign_out(self, access_token: str) -> None:
        """Sign out user from all devices"""
        try:
            self.client.global_sign_out(AccessToken=access_token)

            logger.info("User signed out globally")

        except Exception as e:
            logger.error("Global sign out failed", error=str(e))
            raise

    async def get_hosted_ui_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        identity_provider: str | None = None,
    ) -> str:
        """Get Cognito Hosted UI URL for social login"""
        # Construct Cognito Hosted UI URL based on user pool configuration
        domain = f"https://{self.user_pool_id}.auth.{self.region}.amazoncognito.com"
        url = f"{domain}/oauth2/authorize?client_id={self.client_id}&response_type=code&redirect_uri={redirect_uri}"

        if state:
            url += f"&state={state}"
        if identity_provider:
            url += f"&identity_provider={identity_provider}"

        return url

    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> TokenSet:
        """Exchange authorization code for tokens using Cognito OAuth2 endpoint"""
        try:
            import base64
            import os

            import httpx

            # Get Cognito domain from environment or derive from user pool
            domain = os.getenv("COGNITO_DOMAIN")
            if not domain:
                # Try to derive domain from user pool ID if not configured
                # This is a fallback - COGNITO_DOMAIN should be properly configured
                logger.warning("COGNITO_DOMAIN not configured, attempting to derive from user pool ID")
                domain = f"cognito-{self.user_pool_id.lower()}"

            # Construct the OAuth2 token endpoint URL using Cognito's standard format
            token_endpoint = f"https://{domain}.auth.{self.region}.amazoncognito.com/oauth2/token"

            # Prepare OAuth2 token request payload according to RFC 6749
            payload = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
            }

            # Prepare headers
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": f"BPT-Auth-Service/1.0 boto3/{boto3.__version__}",
            }

            # Add client authentication per OAuth2 spec
            if self.client_secret:
                # Use HTTP Basic authentication with client_id:client_secret (RFC 6749 Section 2.3.1)
                credentials = f"{self.client_id}:{self.client_secret}"
                encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
                headers["Authorization"] = f"Basic {encoded_credentials}"

            logger.debug(
                "Initiating OAuth2 token exchange with Cognito",
                endpoint=token_endpoint,
                client_id=self.client_id,
                domain=domain,
            )

            # Use the same session configuration as the Cognito client for consistency
            # This ensures we inherit proxy settings, timeouts, etc.

            # Make the HTTP request with proper error handling
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0),
                follow_redirects=False,  # OAuth2 endpoints shouldn't redirect
            ) as http_client:
                response = await http_client.post(
                    token_endpoint,
                    data=payload,
                    headers=headers,
                )

                # Handle OAuth2 error responses per RFC 6749 Section 5.2
                if response.status_code != 200:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except (ValueError, KeyError):
                        error_data = {"error": "invalid_response", "error_description": response.text}

                    error_code = error_data.get("error", "unknown_error")
                    error_description = error_data.get("error_description", "Unknown OAuth2 error")

                    logger.error(
                        "OAuth2 token exchange failed",
                        status_code=response.status_code,
                        oauth_error=error_code,
                        error_description=error_description,
                        client_id=self.client_id,
                    )

                    # Map OAuth2 errors to domain-specific exceptions
                    if error_code == "invalid_grant":
                        raise InvalidAuthorizationCodeError("Authorization code is invalid or expired")
                    elif error_code == "invalid_client":
                        raise OAuthClientAuthenticationError("Client authentication failed")
                    else:
                        raise OAuthProviderError(error_code, error_description)

                # Parse successful token response
                try:
                    token_data = response.json()
                except Exception as e:
                    logger.error("Failed to parse token response JSON", error=str(e))
                    raise InvalidTokenResponseError("Failed to parse token response") from e

                # Validate required fields per OAuth2 spec
                required_fields = ["access_token", "token_type"]
                missing_fields = [field for field in required_fields if field not in token_data]
                if missing_fields:
                    logger.error("Token response missing required fields", missing_fields=missing_fields)
                    raise InvalidTokenResponseError(
                        f"Token response missing required fields: {', '.join(missing_fields)}"
                    )

                # Log successful token exchange (without sensitive data)
                logger.info(
                    "OAuth2 token exchange successful",
                    token_type=token_data.get("token_type"),
                    expires_in=token_data.get("expires_in"),
                    has_refresh_token=bool(token_data.get("refresh_token")),
                    has_id_token=bool(token_data.get("id_token")),
                    scope=token_data.get("scope"),
                )

                return TokenSet(
                    access_token=token_data["access_token"],
                    token_type=token_data["token_type"],
                    expires_in=token_data.get("expires_in"),
                    refresh_token=token_data.get("refresh_token"),
                    id_token=token_data.get("id_token"),
                    scope=token_data.get("scope"),
                )

        except (
            InvalidAuthorizationCodeError,
            OAuthClientAuthenticationError,
            InvalidTokenResponseError,
            OAuthProviderError,
        ):
            # Re-raise domain exceptions as-is
            raise
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            logger.error("Network error during OAuth2 token exchange", redirect_uri=redirect_uri, error=str(e))
            raise NetworkError(f"Network error during token exchange: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error during OAuth2 token exchange",
                redirect_uri=redirect_uri,
                error=str(e),
                error_type=type(e).__name__,
            )

            # Wrap unexpected errors in domain exception
            raise TokenExchangeError(f"Token exchange failed: {str(e)}") from e

    def _calculate_secret_hash(self, username: str) -> str:
        """Calculate secret hash for Cognito client"""
        if not self.client_secret:
            return None

        import base64
        import hashlib
        import hmac

        message = username + self.client_id
        dig = hmac.new(
            self.client_secret.encode("utf-8"),
            msg=message.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()

        return base64.b64encode(dig).decode()

    def _parse_user_attributes(self, attributes: list[dict[str, str]]) -> UserAttributes:
        """Parse Cognito user attributes into structured format"""
        attr_dict = {attr["Name"]: attr["Value"] for attr in attributes}

        return UserAttributes(
            sub=attr_dict.get("sub", ""),
            email=attr_dict.get("email"),
            email_verified=attr_dict.get("email_verified", "false").lower() == "true",
            given_name=attr_dict.get("given_name"),
            family_name=attr_dict.get("family_name"),
            phone_number=attr_dict.get("phone_number"),
            phone_number_verified=attr_dict.get("phone_number_verified", "false").lower() == "true",
            preferred_username=attr_dict.get("preferred_username"),
            picture=attr_dict.get("picture"),
            locale=attr_dict.get("locale"),
            zoneinfo=attr_dict.get("zoneinfo"),
        )

    def _parse_code_delivery_details(self, details: dict[str, str] | None) -> CodeDeliveryDetails | None:
        """Parse Cognito code delivery details"""
        if not details:
            return None

        return CodeDeliveryDetails(
            delivery_medium=details["DeliveryMedium"],
            destination=details["Destination"],
            attribute_name=details.get("AttributeName"),
        )
