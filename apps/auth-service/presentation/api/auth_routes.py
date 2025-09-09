from fastapi import APIRouter, HTTPException, Request, Depends, Response
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import structlog

from ...application.use_cases.create_cipher_session import CreateCipherSessionUseCase
from ...application.use_cases.login_user import LoginUserUseCase
from ...domain.value_objects.tokens import CipherEnvelope
from ..schema.auth_schemas import (
    SessionResponse,
    LoginRequest, 
    LoginResponse,
    SignupRequest,
    SignupResponse,
    ConfirmSignupRequest,
    TokenRequest,
    TokenResponse
)

router = APIRouter()
logger = structlog.get_logger(__name__)


def get_cipher_session_use_case(request: Request) -> CreateCipherSessionUseCase:
    """Dependency to get cipher session use case"""
    from ...infrastructure.adapters.crypto.ecdh_kms import ECDHCipher
    
    class CipherServiceAdapter:
        async def generate_cipher_session(self, sid: str):
            from ...infrastructure.adapters.crypto.ecdh_kms import generate_cipher_session_keys
            return generate_cipher_session_keys(sid)
        
        async def decrypt_password(self, private_key_pem, client_public_key_jwk, sid, nonce, ciphertext):
            from ...infrastructure.adapters.crypto.ecdh_kms import decrypt_password_envelope
            return decrypt_password_envelope(private_key_pem, client_public_key_jwk, sid, nonce, ciphertext)
    
    return CreateCipherSessionUseCase(
        cipher_session_repository=request.app.state.cipher_session_repo,
        cipher_service=CipherServiceAdapter()
    )


def get_login_use_case(request: Request) -> LoginUserUseCase:
    """Dependency to get login use case"""
    from ...infrastructure.adapters.boto3.cognito_client import CognitoClientAdapter
    from ...infrastructure.adapters.crypto.ecdh_kms import ECDHCipher
    
    class CipherServiceAdapter:
        async def generate_cipher_session(self, sid: str):
            from ...infrastructure.adapters.crypto.ecdh_kms import generate_cipher_session_keys
            return generate_cipher_session_keys(sid)
        
        async def decrypt_password(self, private_key_pem, client_public_key_jwk, sid, nonce, ciphertext):
            from ...infrastructure.adapters.crypto.ecdh_kms import decrypt_password_envelope
            return decrypt_password_envelope(private_key_pem, client_public_key_jwk, sid, nonce, ciphertext)
    
    class JWTSignerAdapter:
        def __init__(self, signer):
            self.signer = signer
        
        async def sign_jwt(self, claims):
            return self.signer.mint(
                sub=claims.sub,
                sid=claims.sid or "default",
                scopes=claims.scope or "",
                extra=claims.to_dict(),
                ttl=claims.exp - claims.iat
            )
        
        async def get_jwks(self):
            return self.signer.get_jwks()
        
        async def get_current_kid(self):
            return self.signer.kid
    
    auth_config = request.app.state.auth_config
    cognito_client = CognitoClientAdapter(
        user_pool_id=auth_config["cognito_user_pool_id"],
        client_id=auth_config["cognito_client_id"],
        client_secret=auth_config["cognito_client_secret"],
        region=auth_config.get("aws_region", "us-east-1")
    )
    
    return LoginUserUseCase(
        session_repository=request.app.state.session_repo,
        cipher_session_repository=request.app.state.cipher_session_repo,
        cognito_client=cognito_client,
        jwt_signer=JWTSignerAdapter(request.app.state.jwt_signer),
        cipher_service=CipherServiceAdapter(),
        jwt_issuer=auth_config["jwt_issuer"],
        jwt_audience=auth_config["jwt_audience"],
        access_token_ttl=auth_config["access_token_ttl"],
        session_ttl=auth_config["session_ttl"]
    )


@router.post("/session", response_model=SessionResponse)
async def create_session(
    cipher_uc: CreateCipherSessionUseCase = Depends(get_cipher_session_use_case)
):
    """Create a cipher session for password encryption"""
    try:
        result = await cipher_uc.execute()
        return SessionResponse(**result)
        
    except Exception as e:
        logger.error("Session creation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    login_uc: LoginUserUseCase = Depends(get_login_use_case)
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
                sid=request.cipher_envelope.sid
            )
        
        # Execute login
        result = await login_uc.execute(
            username=request.username,
            password=request.password,
            cipher_envelope=cipher_envelope,
            device_info=request.device_info,
            ip_address=request.ip_address,
            user_agent=request.user_agent
        )
        
        # Set httpOnly session cookie
        response.set_cookie(
            key="sid",
            value=result["sid"],
            httponly=True,
            secure=True,  # Use secure in production
            samesite="strict",
            max_age=1800  # 30 minutes
        )
        
        # Remove sid from response body
        response_data = {k: v for k, v in result.items() if k != "sid"}
        
        return LoginResponse(**response_data)
        
    except Exception as e:
        logger.error("Login failed", username=request.username, error=str(e))
        if "Invalid" in str(e) or "unauthorized" in str(e).lower():
            raise HTTPException(status_code=401, detail="Invalid credentials")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/signup", response_model=SignupResponse)
async def signup(request: SignupRequest):
    """Sign up a new user"""
    try:
        # TODO: Implement signup with Cognito
        # This would use CognitoClient.sign_up()
        
        return SignupResponse(
            message="Signup successful. Please check your email for confirmation code.",
            requires_confirmation=True
        )
        
    except Exception as e:
        logger.error("Signup failed", email=request.email, error=str(e))
        raise HTTPException(status_code=400, detail="Signup failed")


@router.post("/confirm-signup")
async def confirm_signup(request: ConfirmSignupRequest):
    """Confirm user signup with verification code"""
    try:
        # TODO: Implement with Cognito
        # This would use CognitoClient.confirm_sign_up()
        
        return {"message": "Account confirmed successfully"}
        
    except Exception as e:
        logger.error("Signup confirmation failed", username=request.username, error=str(e))
        raise HTTPException(status_code=400, detail="Confirmation failed")


@router.post("/token", response_model=TokenResponse)
async def get_token(request: TokenRequest):
    """Exchange OTC or refresh session for access token"""
    try:
        # TODO: Implement token exchange/refresh
        # This handles both OTC from social login and session refresh
        
        return TokenResponse(
            access_token="placeholder_token",
            token_type="Bearer",
            expires_in=900
        )
        
    except Exception as e:
        logger.error("Token exchange failed", error=str(e))
        raise HTTPException(status_code=400, detail="Token exchange failed")


@router.post("/refresh")
async def refresh_token(request: Request):
    """Refresh access token using session"""
    try:
        # TODO: Implement token refresh using session cookie
        # This would validate the session and issue a new access token
        
        return {"access_token": "new_token", "expires_in": 900}
        
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(status_code=401, detail="Token refresh failed")


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout user and invalidate session"""
    try:
        # TODO: Implement logout
        # This would invalidate the session in Redis
        
        # Clear session cookie
        response.delete_cookie("sid", httponly=True)
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error("Logout failed", error=str(e))
        raise HTTPException(status_code=500, detail="Logout failed")


@router.get("/social/providers")
async def get_social_providers():
    """Get available social login providers"""
    try:
        # TODO: Return configured social providers
        return {
            "providers": [
                {"name": "google", "display_name": "Google"},
                {"name": "facebook", "display_name": "Facebook"}
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get social providers", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get providers")


@router.get("/callback")
async def auth_callback(code: str, state: Optional[str] = None):
    """Handle OAuth callback from social providers"""
    try:
        # TODO: Implement OAuth callback handling
        # This would exchange the authorization code for tokens
        
        return {"otc": "one_time_code_placeholder"}
        
    except Exception as e:
        logger.error("Auth callback failed", error=str(e))
        raise HTTPException(status_code=400, detail="Callback failed")