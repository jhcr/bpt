from fastapi import APIRouter, Request
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/.well-known/jwks.json")
async def get_jwks(request: Request):
    """Get JSON Web Key Set for JWT verification"""
    try:
        jwt_signer = request.app.state.jwt_signer
        jwks = jwt_signer.get_jwks()
        
        logger.debug("JWKS requested")
        return jwks
        
    except Exception as e:
        logger.error("JWKS request failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get JWKS")