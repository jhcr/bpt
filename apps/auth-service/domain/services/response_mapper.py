"""Service for mapping between domain entities and response DTOs"""

from domain.entities.provider_entities import (
    ProviderUser,
    TokenSet,
    UserRegistration,
)
from domain.entities.user import User
from domain.responses import OAuthCallbackResponse, ProviderTokenInfo, RegisterUserResponse, UserInfo


class ResponseMapper:
    """Maps domain entities to response DTOs"""

    @staticmethod
    def user_to_user_info(user: User) -> UserInfo:
        """Convert domain User to UserInfo DTO"""
        return UserInfo(
            id=user.id,
            email=user.email,
            given_name=user.given_name,
            family_name=user.family_name,
            email_verified=user.email_verified,
        )

    @staticmethod
    def provider_user_to_user_info(provider_user: ProviderUser, internal_user_id: str) -> UserInfo:
        """Convert ProviderUser to UserInfo DTO"""
        attrs = provider_user.user_attributes
        return UserInfo(
            id=internal_user_id,
            email=attrs.email or "",
            given_name=attrs.given_name,
            family_name=attrs.family_name,
            email_verified=attrs.email_verified,
        )

    @staticmethod
    def token_set_to_provider_token_info(token_set: TokenSet) -> ProviderTokenInfo:
        """Convert TokenSet to ProviderTokenInfo DTO"""
        return ProviderTokenInfo(
            access_token=token_set.access_token,
            id_token=token_set.id_token,
            refresh_token=token_set.refresh_token,
        )

    @staticmethod
    def user_registration_to_response(
        registration: UserRegistration, internal_user_id: str | None = None
    ) -> RegisterUserResponse:
        """Convert UserRegistration to RegisterUserResponse DTO"""
        delivery_medium = None
        destination = None

        if registration.code_delivery_details:
            delivery_medium = registration.code_delivery_details.delivery_medium
            destination = registration.code_delivery_details.destination

        return RegisterUserResponse(
            user_sub=internal_user_id or registration.user_sub,
            confirmation_required=registration.requires_confirmation,
            delivery_medium=delivery_medium,
            destination=destination,
        )

    @staticmethod
    def create_oauth_callback_response(
        sid: str,
        access_token: str,
        token_type: str,
        expires_in: int,
        user: User | UserInfo,
        token_set: TokenSet,
    ) -> OAuthCallbackResponse:
        """Create OAuth callback response from components"""

        # Convert User to UserInfo if needed
        if isinstance(user, User):
            user_info = ResponseMapper.user_to_user_info(user)
        else:
            user_info = user

        provider_tokens = ResponseMapper.token_set_to_provider_token_info(token_set)

        return OAuthCallbackResponse(
            sid=sid,
            access_token=access_token,
            token_type=token_type,
            expires_in=expires_in,
            user=user_info,
            provider_tokens=provider_tokens,
        )
