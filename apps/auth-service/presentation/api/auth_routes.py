import os

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from application.use_cases.create_cipher_session import CreateCipherSessionUseCase
from application.use_cases.forgot_password import ConfirmForgotPasswordUseCase, ForgotPasswordUseCase
from application.use_cases.login_user import LoginUserUseCase
from application.use_cases.logout_user import LogoutUserUseCase
from application.use_cases.oauth_callback import OAuthCallbackUseCase, OAuthStateManager
from application.use_cases.refresh_token import RefreshTokenUseCase
from application.use_cases.register_user import RegisterUserUseCase
from domain.value_objects.tokens import CipherEnvelope
from presentation.schema.auth_schemas import (
    ConfirmForgotPasswordRequest,
    ConfirmSignupRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    ResendConfirmationRequest,
    SessionResponse,
    SignupRequest,
    SignupResponse,
    TokenRequest,
    TokenResponse,
)

router = APIRouter()
logger = structlog.get_logger(__name__)


def get_cipher_session_use_case(request: Request) -> CreateCipherSessionUseCase:
    """Dependency to get cipher session use case"""
    return CreateCipherSessionUseCase(
        cipher_session_repository=request.app.state.cipher_session_repo,
        cipher_service=request.app.state.cipher_service,
    )


def get_login_use_case(request: Request) -> LoginUserUseCase:
    """Dependency to get login use case"""
    auth_config = request.app.state.auth_config

    return LoginUserUseCase(
        session_repository=request.app.state.session_repo,
        cipher_session_repository=request.app.state.cipher_session_repo,
        cognito_client=request.app.state.cognito_client,
        jwt_signer=request.app.state.jwt_signer_adapter,
        cipher_service=request.app.state.cipher_service,
        jwt_issuer=auth_config["jwt_issuer"],
        jwt_audience=auth_config["jwt_audience"],
        access_token_ttl=auth_config["access_token_ttl"],
        session_ttl=auth_config["session_ttl"],
    )


def get_register_use_case(request: Request) -> RegisterUserUseCase:
    """Dependency to get register user use case"""
    return RegisterUserUseCase(cognito_client=request.app.state.cognito_client)


def get_refresh_token_use_case(request: Request) -> RefreshTokenUseCase:
    """Dependency to get refresh token use case"""
    auth_config = request.app.state.auth_config

    return RefreshTokenUseCase(
        session_repository=request.app.state.session_repo,
        cognito_client=request.app.state.cognito_client,
        jwt_signer=request.app.state.jwt_signer_adapter,
        jwt_issuer=auth_config["jwt_issuer"],
        jwt_audience=auth_config["jwt_audience"],
        access_token_ttl=auth_config["access_token_ttl"],
    )


def get_logout_use_case(request: Request) -> LogoutUserUseCase:
    """Dependency to get logout use case"""
    return LogoutUserUseCase(
        session_repository=request.app.state.session_repo,
        cognito_client=request.app.state.cognito_client,
    )


def get_forgot_password_use_case(request: Request) -> ForgotPasswordUseCase:
    """Dependency to get forgot password use case"""
    return ForgotPasswordUseCase(
        cognito_client=request.app.state.cognito_client,
        session_repository=request.app.state.session_repo,
    )


def get_confirm_forgot_password_use_case(request: Request) -> ConfirmForgotPasswordUseCase:
    """Dependency to get confirm forgot password use case"""
    return ConfirmForgotPasswordUseCase(
        cognito_client=request.app.state.cognito_client,
        session_repository=request.app.state.session_repo,
    )


def get_oauth_callback_use_case(request: Request) -> OAuthCallbackUseCase:
    """Dependency to get OAuth callback use case"""
    auth_config = request.app.state.auth_config

    return OAuthCallbackUseCase(
        cognito_client=request.app.state.cognito_client,
        session_repository=request.app.state.session_repo,
        jwt_signer=request.app.state.jwt_signer_adapter,
        jwt_issuer=auth_config["jwt_issuer"],
        jwt_audience=auth_config["jwt_audience"],
        access_token_ttl=auth_config["access_token_ttl"],
        session_ttl=auth_config["session_ttl"],
    )


@router.post("/session", response_model=SessionResponse)
async def create_session(
    cipher_uc: CreateCipherSessionUseCase = Depends(get_cipher_session_use_case),
):
    """Create a cipher session for password encryption"""
    try:
        cipher_session = await cipher_uc.execute()
        return SessionResponse(sid=cipher_session.sid, server_public_key_jwk=cipher_session.server_public_key_jwk)

    except Exception as e:
        logger.error("Session creation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create session") from e


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    login_uc: LoginUserUseCase = Depends(get_login_use_case),
):
    """Login with username/password or cipher envelope"""
    try:
        # Prepare cipher envelope if provided
        cipher_envelope = None
        if request.cipher_envelope:
            cipher_envelope = CipherEnvelope(
                client_public_key_jwk=request.cipher_envelope.client_public_key_jwk,
                nonce=request.cipher_envelope.nonce,
                password_enc=request.cipher_envelope.password_enc,
                sid=request.cipher_envelope.sid,
            )

        # Execute login
        result = await login_uc.execute(
            username=request.username,
            password=request.password,
            cipher_envelope=cipher_envelope,
            device_info=request.device_info,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
        )

        # Set httpOnly session cookie
        response.set_cookie(
            key="sid",
            value=result.sid,
            httponly=True,
            secure=True,  # Use secure in production
            samesite="strict",
            max_age=1800,  # 30 minutes
        )

        # Build response data (exclude sid from body)
        response_data = {
            "access_token": result.access_token,
            "token_type": result.token_type,
            "expires_in": result.expires_in,
            "user": {
                "id": result.user.id,
                "email": result.user.email,
                "given_name": result.user.given_name,
                "family_name": result.user.family_name,
                "email_verified": result.user.email_verified,
            },
        }

        return LoginResponse(**response_data)

    except Exception as e:
        logger.error("Login failed", username=request.username, error=str(e))
        if "Invalid" in str(e) or "unauthorized" in str(e).lower():
            raise HTTPException(status_code=401, detail="Invalid credentials") from e
        raise HTTPException(status_code=500, detail="Login failed") from e


@router.post("/signup", response_model=SignupResponse)
async def signup(
    request: SignupRequest,
    register_uc: RegisterUserUseCase = Depends(get_register_use_case),
):
    """Sign up a new user"""
    try:
        result = await register_uc.execute(
            email=request.email,
            password=request.password,
            given_name=request.given_name,
            family_name=request.family_name,
            phone_number=request.phone_number,
        )

        logger.info("User signup successful", email=request.email, user_sub=result.user_sub)

        return SignupResponse(
            message="User registration successful",
            requires_confirmation=result.confirmation_required,
        )

    except Exception as e:
        logger.error("Signup failed", email=request.email, error=str(e))

        # Handle specific domain errors
        if "already exists" in str(e).lower():
            raise HTTPException(status_code=409, detail="User with this email already exists") from e
        elif "password" in str(e).lower() and ("requirement" in str(e).lower() or "invalid" in str(e).lower()):
            raise HTTPException(status_code=400, detail="Password does not meet requirements") from e
        elif "validation" in str(e).lower() or "invalid" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e)) from e
        else:
            raise HTTPException(status_code=500, detail="Registration failed") from e


@router.post("/confirm-signup")
async def confirm_signup(
    request: ConfirmSignupRequest,
    register_uc: RegisterUserUseCase = Depends(get_register_use_case),
):
    """Confirm user signup with verification code"""
    try:
        # Use the cognito client from the register use case to confirm signup
        await register_uc.cognito_client.confirm_sign_up(
            username=request.username,
            confirmation_code=request.confirmation_code,
        )

        logger.info("User signup confirmed", username=request.username)
        return {"message": "Account confirmed successfully"}

    except Exception as e:
        logger.error("Signup confirmation failed", username=request.username, error=str(e))

        # Handle specific Cognito errors
        if "CodeMismatchException" in str(e):
            raise HTTPException(status_code=400, detail="Invalid confirmation code") from e
        elif "ExpiredCodeException" in str(e):
            raise HTTPException(status_code=400, detail="Confirmation code has expired") from e
        elif "UserNotFoundException" in str(e):
            raise HTTPException(status_code=404, detail="User not found") from e
        else:
            raise HTTPException(status_code=400, detail="Confirmation failed") from e


@router.post("/resend-confirmation")
async def resend_confirmation(
    request: ResendConfirmationRequest,
    register_uc: RegisterUserUseCase = Depends(get_register_use_case),
):
    """Resend confirmation code for user signup"""
    try:
        await register_uc.cognito_client.resend_confirmation_code(username=request.username)

        logger.info("Confirmation code resent", username=request.username)
        return {"message": "Confirmation code sent successfully"}

    except Exception as e:
        logger.error("Failed to resend confirmation code", username=request.username, error=str(e))

        if "UserNotFoundException" in str(e):
            raise HTTPException(status_code=404, detail="User not found") from e
        elif "InvalidParameterException" in str(e):
            raise HTTPException(status_code=400, detail="User already confirmed") from e
        else:
            raise HTTPException(status_code=400, detail="Failed to resend confirmation code") from e


@router.post("/token", response_model=TokenResponse)
async def get_token(
    token_request: TokenRequest,
    refresh_uc: RefreshTokenUseCase = Depends(get_refresh_token_use_case),
):
    """Exchange OTC or refresh session for access token"""
    try:
        if token_request.grant_type == "refresh_token" and token_request.refresh_token:
            # Refresh token flow
            result = await refresh_uc.execute_with_refresh_token(token_request.refresh_token)

            return TokenResponse(
                access_token=result["access_token"],
                token_type=result["token_type"],
                expires_in=result["expires_in"],
                refresh_token=result.get("refresh_token"),
            )
        else:
            # Other grant types not implemented yet
            raise HTTPException(status_code=400, detail="Unsupported grant type or missing refresh_token")

    except Exception as e:
        logger.error("Token exchange failed", grant_type=token_request.grant_type, error=str(e))
        if "Invalid" in str(e) or "expired" in str(e).lower():
            raise HTTPException(status_code=401, detail="Invalid or expired token") from e
        raise HTTPException(status_code=400, detail="Token exchange failed") from e


@router.post("/refresh")
async def refresh_token(
    request: Request,
    refresh_uc: RefreshTokenUseCase = Depends(get_refresh_token_use_case),
):
    """Refresh access token using session cookie"""
    try:
        # Get session ID from cookie
        sid = request.cookies.get("sid")
        if not sid:
            raise HTTPException(status_code=401, detail="No session found")

        # Refresh using session
        result = await refresh_uc.execute_with_session(sid)

        return {
            "access_token": result["access_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
        }

    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        if "Session" in str(e) and ("expired" in str(e).lower() or "invalid" in str(e).lower()):
            raise HTTPException(status_code=401, detail="Session expired or invalid") from e
        raise HTTPException(status_code=401, detail="Token refresh failed") from e


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    logout_request: LogoutRequest | None = None,
    logout_uc: LogoutUserUseCase = Depends(get_logout_use_case),
):
    """Logout user and invalidate session"""
    try:
        # Get session ID from cookie
        sid = request.cookies.get("sid")

        # Get access token from Authorization header if available
        access_token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            access_token = auth_header[7:]

        # Determine if global logout is requested
        global_logout = logout_request.global_logout if logout_request else False

        # Execute logout
        result = await logout_uc.execute(
            sid=sid,
            access_token=access_token,
            global_logout=global_logout,
        )

        # Clear session cookie regardless of whether session existed
        response.delete_cookie(key="sid", httponly=True, secure=True, samesite="strict")

        logger.info(
            "User logout completed",
            session_invalidated=result["session_invalidated"],
            global_logout=result["global_logout"],
        )

        return result

    except Exception as e:
        logger.error("Logout failed", error=str(e))
        # Still clear the cookie even if logout failed
        response.delete_cookie("sid", httponly=True)
        raise HTTPException(status_code=500, detail="Logout failed") from e


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    forgot_password_uc: ForgotPasswordUseCase = Depends(get_forgot_password_use_case),
):
    """Initiate forgot password flow"""
    try:
        result = await forgot_password_uc.execute(username=request.username)

        logger.info("Forgot password initiated", username=request.username)
        return result

    except Exception as e:
        logger.error("Forgot password failed", username=request.username, error=str(e))
        if "too many" in str(e).lower() or "limit" in str(e).lower():
            raise HTTPException(status_code=429, detail=str(e)) from e
        raise HTTPException(status_code=400, detail="Failed to initiate password reset") from e


@router.post("/confirm-forgot-password")
async def confirm_forgot_password(
    request: ConfirmForgotPasswordRequest,
    confirm_forgot_password_uc: ConfirmForgotPasswordUseCase = Depends(get_confirm_forgot_password_use_case),
):
    """Confirm forgot password with new password"""
    try:
        result = await confirm_forgot_password_uc.execute(
            username=request.username,
            confirmation_code=request.confirmation_code,
            new_password=request.new_password,
        )

        logger.info("Forgot password confirmed", username=request.username)
        return result

    except Exception as e:
        logger.error("Confirm forgot password failed", username=request.username, error=str(e))
        if "invalid" in str(e).lower() and "code" in str(e).lower():
            raise HTTPException(status_code=400, detail="Invalid confirmation code") from e
        elif "expired" in str(e).lower():
            raise HTTPException(status_code=400, detail="Confirmation code has expired") from e
        elif "password" in str(e).lower() and "requirement" in str(e).lower():
            raise HTTPException(status_code=400, detail="Password does not meet requirements") from e
        elif "user not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="User not found") from e
        else:
            raise HTTPException(status_code=400, detail="Password reset failed") from e


@router.get("/social/providers")
async def get_social_providers():
    """Get available social login providers"""
    try:
        # Read from configuration or environment
        providers = []

        # Check if Google OAuth is configured
        if os.getenv("GOOGLE_OAUTH_CLIENT_ID"):
            providers.append(
                {
                    "name": "google",
                    "display_name": "Google",
                    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
                }
            )

        # Check if other providers are configured
        if os.getenv("FACEBOOK_OAUTH_CLIENT_ID"):
            providers.append(
                {
                    "name": "facebook",
                    "display_name": "Facebook",
                    "authorization_url": "https://www.facebook.com/v18.0/dialog/oauth",
                }
            )

        return {"providers": providers}

    except Exception as e:
        logger.error("Failed to get social providers", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get providers") from e


@router.get("/social/{provider}/authorize")
async def get_oauth_authorize_url(
    provider: str,
    request: Request,
    redirect_after_login: str | None = None,
):
    """Get OAuth authorization URL for a specific provider"""
    try:
        # Validate provider
        supported_providers = ["google", "facebook", "amazon", "apple"]
        if provider not in supported_providers:
            raise HTTPException(
                status_code=400, detail=f"Unsupported provider. Supported: {', '.join(supported_providers)}"
            )

        # Generate state for CSRF protection
        state_manager = OAuthStateManager(request.app.state.session_repo)
        state = await state_manager.generate_state(redirect_after_login)

        # Get redirect URI
        redirect_uri = os.getenv("OAUTH_REDIRECT_URI", f"{request.base_url}auth/callback")

        # In a real implementation, you'd use the Cognito hosted UI URL
        # For now, construct a basic OAuth URL
        auth_config = request.app.state.auth_config
        cognito_domain = os.getenv("COGNITO_DOMAIN", "your-app")
        region = auth_config.get("aws_region", "us-east-1")
        client_id = auth_config["cognito_client_id"]

        # Construct Cognito hosted UI URL
        base_url = f"https://{cognito_domain}.auth.{region}.amazoncognito.com/oauth2/authorize"

        from urllib.parse import urlencode

        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": "openid email profile",
        }

        # Add identity provider if specified
        if provider != "cognito":
            params["identity_provider"] = provider.title()

        authorization_url = f"{base_url}?{urlencode(params)}"

        logger.info(
            "OAuth authorization URL generated",
            provider=provider,
            state=state,
            redirect_after_login=redirect_after_login,
        )

        return {
            "authorization_url": authorization_url,
            "state": state,
            "provider": provider,
        }

    except Exception as e:
        logger.error("Failed to generate OAuth URL", provider=provider, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate authorization URL") from e


@router.get("/callback")
async def auth_callback(
    request: Request,
    response: Response,
    code: str,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    oauth_uc: OAuthCallbackUseCase = Depends(get_oauth_callback_use_case),
):
    """Handle OAuth callback from social providers"""
    try:
        # Check for OAuth errors first
        if error:
            logger.warning("OAuth callback error", error=error, error_description=error_description)
            raise HTTPException(status_code=400, detail=f"OAuth error: {error_description or error}")

        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")

        # Validate state parameter for CSRF protection
        if state:
            # In production, validate state against stored value in Redis
            state_manager = OAuthStateManager(request.app.state.session_repo)
            state_data = await state_manager.validate_state(state)
            if not state_data or not state_data.get("valid"):
                raise HTTPException(status_code=400, detail="Invalid state parameter")
            logger.debug("OAuth state validated", state=state)

        # Get redirect URI from environment or configuration
        redirect_uri = os.getenv("OAUTH_REDIRECT_URI", f"{request.base_url}auth/callback")

        # Process the OAuth callback
        result = await oauth_uc.execute(
            authorization_code=code,
            redirect_uri=str(redirect_uri),
            state=state,
        )

        # Set session cookie
        response.set_cookie(
            key="sid",
            value=result["sid"],
            httponly=True,
            secure=True,  # Use secure in production
            samesite="strict",
            max_age=1800,  # 30 minutes
        )

        logger.info(
            "OAuth callback processed successfully", user_id=result["user"]["id"], email=result["user"]["email"]
        )

        # Return success response (for API clients)
        # In a web app, you might redirect to a success page
        return {
            "message": "OAuth login successful",
            "user": result["user"],
            "access_token": result["access_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("OAuth callback failed", code=code[:10] + "..." if code else None, state=state, error=str(e))

        # Handle specific OAuth and Cognito errors
        error_message = str(e).lower()

        if "invalid" in error_message and "code" in error_message:
            raise HTTPException(status_code=400, detail="Authorization code is invalid or expired") from e
        elif "authentication failed" in error_message or "client" in error_message:
            raise HTTPException(status_code=401, detail="OAuth client authentication failed") from e
        elif "token exchange" in error_message:
            raise HTTPException(status_code=400, detail="Failed to exchange authorization code for tokens") from e
        elif "user info" in error_message:
            raise HTTPException(status_code=400, detail="Failed to retrieve user information from provider") from e
        else:
            raise HTTPException(status_code=500, detail="OAuth callback processing failed") from e
