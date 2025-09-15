import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from application.use_cases.svc_token import ServiceTokenUseCase
from presentation.schema.svc_token_schemas import ServiceTokenRequest, ServiceTokenResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


def get_service_token_use_case(request: Request) -> ServiceTokenUseCase:
    """Dependency to get service token use case"""
    return ServiceTokenUseCase(signer=request.app.state.jwt_signer)


@router.post("/svc/token", response_model=ServiceTokenResponse)
async def create_service_token(
    request: ServiceTokenRequest,
    svc_token_uc: ServiceTokenUseCase = Depends(get_service_token_use_case),
):
    """Create a service token for service-to-service authentication"""
    try:
        result = await svc_token_uc.execute(
            client_id=request.client_id,
            client_secret=request.client_secret,
            sub_spn=request.sub_spn,
            scope=request.scope,
            actor_sub=request.actor_sub,
            actor_scope=request.actor_scope,
            actor_roles=request.actor_roles,
        )

        logger.info("Service token issued", sub_spn=request.sub_spn)
        return ServiceTokenResponse(**result)

    except Exception as e:
        logger.error("Service token creation failed", sub_spn=request.sub_spn, error=str(e))

        if "Invalid client" in str(e) or "unauthorized" in str(e).lower():
            raise HTTPException(status_code=401, detail="Invalid client credentials") from e

        raise HTTPException(status_code=500, detail="Service token creation failed") from e
