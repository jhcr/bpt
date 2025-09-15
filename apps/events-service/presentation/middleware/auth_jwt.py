# Assumptions:
# - JWT middleware for user and service token validation
# - Integration with shared auth modules
# - FastAPI dependency injection pattern

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from framework.auth.jwt_verify import JWTVerifier, create_jwt_verifier
from framework.auth.principals import Principal, create_service_principal

logger = structlog.get_logger(__name__)
security = HTTPBearer()


def get_jwt_verifier() -> JWTVerifier:
    """Create JWT verifier instance for service tokens only"""
    # In production, these would come from environment variables
    jwks_uri = "https://auth.example.com/.well-known/jwks.json"  # Replace with actual JWKS URL
    issuer = "https://auth.example.com"
    audience = "events-service"

    return create_jwt_verifier(jwks_uri, issuer, audience)


async def get_service_principal(
    credentials=Depends(security),
    jwt_verifier: JWTVerifier = Depends(get_jwt_verifier),
) -> Principal:
    """
    Extract and verify service JWT token, return Principal
    Events service only accepts service tokens.
    """
    try:
        token = credentials.credentials

        # Verify JWT token
        claims = jwt_verifier.verify(token)

        # Only accept service tokens
        token_use = claims.get("token_use", "access")
        if token_use != "svc":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Service token required - events service only accepts service-to-service calls",
            )

        # Create service principal
        return create_service_principal(claims)

    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Service token verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service token"
        ) from None
