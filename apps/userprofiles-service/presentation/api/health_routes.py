# Health check routes for userprofiles-service

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()
logger = structlog.get_logger(__name__)


class HealthResponse(BaseModel):
    status: str
    service: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", service="userprofiles-service")


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_check(request: Request):
    """Readiness check with database connectivity"""
    try:
        # Check database connection pool
        async with request.app.state.db_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()

        return ReadinessResponse(status="ready", checks={"database": "ok"})
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail={"status": "not_ready", "checks": {"database": "failed"}}) from None


@router.get("/health/live", response_model=HealthResponse)
async def liveness_check():
    """Liveness check endpoint"""
    return HealthResponse(status="alive", service="userprofiles-service")
