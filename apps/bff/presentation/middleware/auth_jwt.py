from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import structlog

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared', 'python'))
from shared_auth.jwt_verify import create_jwt_verifier, JWTVerifier
from shared_auth.principals import Principal, create_user_principal

logger = structlog.get_logger(__name__)
security = HTTPBearer()


def get_jwt_verifier(request: Request) -> JWTVerifier:
    """Get JWT verifier from app state"""
    return request.app.state.jwt_verifier


async def get_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_verifier: JWTVerifier = Depends(get_jwt_verifier)
) -> Principal:
    """
    Extract and verify JWT token, return Principal
    
    Args:
        credentials: JWT token from Authorization header
        jwt_verifier: JWT verifier instance
        
    Returns:
        Principal representing the authenticated user/service
        
    Raises:
        HTTPException: If token is invalid or missing required claims
    """
    try:
        token = credentials.credentials
        
        # Verify JWT token
        claims = jwt_verifier.verify(token)
        
        # Create principal based on token type
        token_use = claims.get("token_use", "access")
        
        if token_use == "access":
            # User access token
            principal = create_user_principal(claims)
        elif token_use == "svc":
            # Service token - BFF should not normally receive these directly
            # from end users, but might get them from other services
            from shared_auth.principals import create_service_principal
            principal = create_service_principal(claims)
        else:
            logger.warning("Unknown token type", token_use=token_use)
            raise HTTPException(status_code=401, detail="Unknown token type")
        
        # Log authentication success
        logger.debug("Authentication successful", 
                    sub=principal.sub, 
                    token_use=principal.token_use,
                    scopes=principal.scopes)
        
        return principal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Authentication failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid authentication token")


async def require_scope(required_scope: str) -> None:
    """
    Dependency to require a specific scope
    
    Args:
        required_scope: The scope that is required
    """
    def scope_checker(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.has_scope(required_scope):
            logger.warning("Insufficient scope", 
                          required=required_scope, 
                          available=principal.scopes,
                          sub=principal.sub)
            raise HTTPException(
                status_code=403, 
                detail=f"Insufficient scope. Required: {required_scope}"
            )
        return principal
    
    return scope_checker


def require_any_scope(*required_scopes: str):
    """
    Dependency to require any of the specified scopes
    
    Args:
        required_scopes: One or more scopes, any of which satisfies the requirement
    """
    def scope_checker(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.has_any_scope(list(required_scopes)):
            logger.warning("Insufficient scope", 
                          required_any=required_scopes, 
                          available=principal.scopes,
                          sub=principal.sub)
            raise HTTPException(
                status_code=403, 
                detail=f"Insufficient scope. Required one of: {', '.join(required_scopes)}"
            )
        return principal
    
    return scope_checker


def require_role(required_role: str):
    """
    Dependency to require a specific role
    
    Args:
        required_role: The role that is required
    """
    def role_checker(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.has_role(required_role):
            logger.warning("Insufficient role", 
                          required=required_role, 
                          available=principal.roles,
                          sub=principal.sub)
            raise HTTPException(
                status_code=403, 
                detail=f"Insufficient role. Required: {required_role}"
            )
        return principal
    
    return role_checker


# Common permission dependencies
require_user_read = Depends(require_scope("user.read"))
require_user_write = Depends(require_scope("user.write"))
require_usersettings_read = Depends(require_scope("usersettings.read"))
require_usersettings_write = Depends(require_scope("usersettings.write"))