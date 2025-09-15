"""Service for mapping between provider entities and domain entities"""

import uuid
from datetime import datetime

from domain.entities.provider_entities import AdminProviderUser, ProviderUser
from domain.entities.user import User


class UserMapper:
    """Maps provider entities to domain entities"""

    @staticmethod
    def provider_user_to_domain_user(provider_user: ProviderUser, internal_user_id: str | None = None) -> User:
        """Convert ProviderUser to domain User entity"""
        attrs = provider_user.user_attributes

        return User(
            id=internal_user_id or str(uuid.uuid4()),
            provider_sub=attrs.sub,
            email=attrs.email or "",
            email_verified=attrs.email_verified,
            phone_number=attrs.phone_number,
            phone_verified=attrs.phone_number_verified,
            given_name=attrs.given_name,
            family_name=attrs.family_name,
            preferred_username=attrs.preferred_username,
            picture=attrs.picture,
            locale=attrs.locale,
            zoneinfo=attrs.zoneinfo,
            updated_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            enabled=provider_user.enabled,
            user_status=provider_user.user_status or "CONFIRMED",
            provider_metadata={
                "username": provider_user.username,
                "user_status": provider_user.user_status,
            },
        )

    @staticmethod
    def admin_provider_user_to_domain_user(admin_user: AdminProviderUser, internal_user_id: str | None = None) -> User:
        """Convert AdminProviderUser to domain User entity"""
        attrs = admin_user.user_attributes

        return User(
            id=internal_user_id or str(uuid.uuid4()),
            provider_sub=attrs.sub,
            email=attrs.email or "",
            email_verified=attrs.email_verified,
            phone_number=attrs.phone_number,
            phone_verified=attrs.phone_number_verified,
            given_name=attrs.given_name,
            family_name=attrs.family_name,
            preferred_username=attrs.preferred_username,
            picture=attrs.picture,
            locale=attrs.locale,
            zoneinfo=attrs.zoneinfo,
            updated_at=admin_user.user_last_modified_date or datetime.utcnow(),
            created_at=admin_user.user_create_date or datetime.utcnow(),
            enabled=admin_user.enabled,
            user_status=admin_user.user_status,
            provider_metadata={
                "username": admin_user.username,
                "user_status": admin_user.user_status,
                "user_create_date": admin_user.user_create_date.isoformat() if admin_user.user_create_date else None,
                "user_last_modified_date": admin_user.user_last_modified_date.isoformat()
                if admin_user.user_last_modified_date
                else None,
            },
        )
