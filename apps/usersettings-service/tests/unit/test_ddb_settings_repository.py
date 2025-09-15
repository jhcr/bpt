# Assumptions:
# - Using pytest for testing framework
# - Using moto for DynamoDB mocking
# - Testing OCC (optimistic concurrency control) behavior

import pytest
import boto3
from moto import mock_dynamodb

from infrastructure.adapters.ddb_settings_repository import DdbSettingsRepository
from domain.entities.user_setting import UserSetting
from domain.errors import VersionConflictError


@pytest.fixture
def dynamodb_table():
    """Create mock DynamoDB table"""
    with mock_dynamodb():
        # Create DynamoDB resource
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Create table
        table = dynamodb.create_table(
            TableName="test_user_settings",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "category", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "category", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Wait for table to be created
        table.wait_until_exists()

        yield table


@pytest.fixture
def repository(dynamodb_table):
    """Create repository instance with mock table"""
    dynamodb_resource = boto3.resource("dynamodb", region_name="us-east-1")
    return DdbSettingsRepository("test_user_settings", dynamodb_resource=dynamodb_resource)


class TestDdbSettingsRepository:
    """Test cases for DynamoDB settings repository"""

    @pytest.mark.asyncio
    async def test_get_nonexistent_setting(self, repository):
        """Test getting non-existent setting returns None"""
        result = await repository.get_setting("user123", "preferences")
        assert result is None

    @pytest.mark.asyncio
    async def test_put_new_setting(self, repository):
        """Test putting new setting (OCC first write)"""
        user_id = "user123"
        category = "preferences"
        data = {"theme": "dark", "language": "en"}

        # Create UserSetting entity
        setting = UserSetting.create(user_id=user_id, category=category, data=data)

        # First write (no expected version)
        result = await repository.update_setting(setting)

        assert result is not None
        assert result.user_id == user_id
        assert result.category == category
        assert result.data == data
        assert result.version == 1
        assert result.updated_at is not None

    @pytest.mark.asyncio
    async def test_put_update_setting_success(self, repository):
        """Test successful update with correct version"""
        user_id = "user123"
        category = "preferences"
        initial_data = {"theme": "light", "language": "en"}
        updated_data = {"theme": "dark", "language": "en"}

        # First write
        setting1 = UserSetting.create(user_id=user_id, category=category, data=initial_data)
        result1 = await repository.update_setting(setting1)
        assert result1.version == 1

        # Update with correct version
        setting2 = UserSetting(
            user_id=user_id,
            category=category,
            data=updated_data,
            version=1,  # Use current version
            updated_at=result1.updated_at,
        )
        result2 = await repository.update_setting(setting2)

        assert result2 is not None
        assert result2.version == 2
        assert result2.data == updated_data

    @pytest.mark.asyncio
    async def test_put_update_version_conflict(self, repository):
        """Test version conflict on update"""
        user_id = "user123"
        category = "preferences"
        initial_data = {"theme": "light"}
        updated_data = {"theme": "dark"}

        # First write
        setting1 = UserSetting.create(user_id=user_id, category=category, data=initial_data)
        result1 = await repository.update_setting(setting1)
        assert result1.version == 1

        # Try to update with wrong version
        setting2 = UserSetting(
            user_id=user_id,
            category=category,
            data=updated_data,
            version=99,  # Wrong version
            updated_at=result1.updated_at,
        )

        # Should raise VersionConflictError
        with pytest.raises(VersionConflictError):
            await repository.update_setting(setting2)

    @pytest.mark.asyncio
    async def test_get_existing_setting(self, repository):
        """Test getting existing setting"""
        user_id = "user123"
        category = "preferences"
        data = {"theme": "dark", "notifications": True}

        # Put setting first
        setting = UserSetting.create(user_id=user_id, category=category, data=data)
        await repository.update_setting(setting)

        # Get setting
        result = await repository.get_setting(user_id, category)

        assert result is not None
        assert result.user_id == user_id
        assert result.category == category
        assert result.data == data
        assert result.version == 1

    @pytest.mark.asyncio
    async def test_multiple_categories_same_user(self, repository):
        """Test multiple categories for same user"""
        user_id = "user123"

        # Put different categories
        prefs_data = {"theme": "dark"}
        notif_data = {"email": True, "push": False}

        setting1 = UserSetting.create(user_id=user_id, category="preferences", data=prefs_data)
        setting2 = UserSetting.create(user_id=user_id, category="notifications", data=notif_data)

        result1 = await repository.update_setting(setting1)
        result2 = await repository.update_setting(setting2)

        assert result1.data == prefs_data
        assert result2.data == notif_data

        # Get each category
        prefs = await repository.get_setting(user_id, "preferences")
        notifs = await repository.get_setting(user_id, "notifications")

        assert prefs.data == prefs_data
        assert notifs.data == notif_data

    @pytest.mark.asyncio
    async def test_concurrent_updates_simulation(self, repository):
        """Test simulation of concurrent updates"""
        user_id = "user123"
        category = "preferences"

        # Initial write
        initial_data = {"counter": 0}
        setting1 = UserSetting.create(user_id=user_id, category=category, data=initial_data)
        result1 = await repository.update_setting(setting1)
        version1 = result1.version

        # Simulate two concurrent readers getting same version
        current_setting = await repository.get_setting(user_id, category)
        assert current_setting.version == version1

        # First writer succeeds
        update1_data = {"counter": 1}
        setting2 = UserSetting(
            user_id=user_id,
            category=category,
            data=update1_data,
            version=version1,
            updated_at=current_setting.updated_at,
        )
        result2 = await repository.update_setting(setting2)
        assert result2 is not None
        assert result2.version == version1 + 1

        # Second writer fails (stale version)
        update2_data = {"counter": 2}
        setting3 = UserSetting(
            user_id=user_id,
            category=category,
            data=update2_data,
            version=version1,  # Stale version
            updated_at=current_setting.updated_at,
        )

        # Should raise VersionConflictError due to version conflict
        with pytest.raises(VersionConflictError):
            await repository.update_setting(setting3)
