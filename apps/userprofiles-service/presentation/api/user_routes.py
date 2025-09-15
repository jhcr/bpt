import os
import sys

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from application.use_cases.create_user import CreateUser
from application.use_cases.get_user import GetUser
from application.use_cases.list_users import ListUsers
from application.use_cases.update_user import UpdateUser
from presentation.schema.user_schemas import CreateUserRequest, UpdateUserRequest, UserListResponse, UserResponse

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["users"])


# Dependency functions for FastAPI DI
def get_get_user_use_case(request: Request) -> GetUser:
    """Dependency to get GetUser use case"""
    return request.app.state.get_user_uc


def get_create_user_use_case(request: Request) -> CreateUser:
    """Dependency to get CreateUser use case"""
    return request.app.state.create_user_uc


def get_update_user_use_case(request: Request) -> UpdateUser:
    """Dependency to get UpdateUser use case"""
    return request.app.state.update_user_uc


def get_list_users_use_case(request: Request) -> ListUsers:
    """Dependency to get ListUsers use case"""
    return request.app.state.list_users_uc


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    get_user: GetUser = Depends(get_get_user_use_case),
):
    """Get user by ID"""
    user = await get_user.by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_entity(user)


@router.get("/users/cognito/{cognito_sub}", response_model=UserResponse)
async def get_user_by_cognito_sub(
    cognito_sub: str,
    get_user: GetUser = Depends(get_get_user_use_case),
):
    """Get user by Cognito subject"""
    user = await get_user.by_cognito_sub(cognito_sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_entity(user)


@router.get("/users", response_model=UserListResponse)
async def list_users(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    list_users_uc: ListUsers = Depends(get_list_users_use_case),
):
    """List users with pagination"""
    users = await list_users_uc.execute(limit=limit, offset=offset)
    total = await list_users_uc.count()

    return UserListResponse(
        users=[UserResponse.from_entity(user) for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    request: CreateUserRequest,
    create_user_uc: CreateUser = Depends(get_create_user_use_case),
):
    """Create new user"""
    try:
        user = await create_user_uc.execute(
            cognito_sub=request.cognito_sub,
            email=request.email,
            display_name=request.display_name,
            avatar_url=request.avatar_url,
            phone=request.phone,
        )
        return UserResponse.from_entity(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    update_user_uc: UpdateUser = Depends(get_update_user_use_case),
):
    """Update user"""
    try:
        user = await update_user_uc.execute(
            user_id=user_id,
            email=request.email,
            display_name=request.display_name,
            avatar_url=request.avatar_url,
            phone=request.phone,
            is_active=request.is_active,
        )
        return UserResponse.from_entity(user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
