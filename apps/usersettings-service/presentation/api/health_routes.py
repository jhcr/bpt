# Assumptions:
# - Health check endpoints for service monitoring
# - Simple status response for container orchestration

from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", service="usersettings-service")


@router.get("/health/ready", response_model=HealthResponse)
async def readiness_check():
    """Readiness check endpoint"""
    # TODO: Add checks for DynamoDB connectivity
    return HealthResponse(status="ready", service="usersettings-service")


@router.get("/health/live", response_model=HealthResponse)
async def liveness_check():
    """Liveness check endpoint"""
    return HealthResponse(status="alive", service="usersettings-service")
