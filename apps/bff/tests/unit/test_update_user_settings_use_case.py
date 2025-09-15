# Assumptions:
# - Using pytest for testing framework
# - Testing UpdateUserSettings and GetUserSettings use cases
# - Testing error handling and version conflicts

from unittest.mock import AsyncMock, Mock

import pytest
import structlog

from application.use_cases.update_user_settings import GetUserSettings, UpdateUserSettings
from domain.entities.user import UserSettings, UserSettingsCollection

# Mock the logger to avoid log output during tests
structlog.get_logger = Mock(return_value=Mock())


class TestUpdateUserSettingsUseCase:
    """Test cases for UpdateUserSettings use case"""

    @pytest.fixture
    def mock_usersettings_port(self):
        """Mock UserSettings port"""
        return AsyncMock()

    @pytest.fixture
    def update_settings_use_case(self, mock_usersettings_port):
        """Create UpdateUserSettings use case instance"""
        return UpdateUserSettings(usersettings_port=mock_usersettings_port)

    @pytest.mark.asyncio
    async def test_update_settings_success(self, update_settings_use_case, mock_usersettings_port):
        """Test successful settings update"""
        # Arrange
        user_id = "user-123"
        category = "preferences"
        settings_data = {"theme": "dark", "language": "en"}
        expected_version = 1

        returned_data = {
            "user_id": user_id,
            "category": category,
            "data": settings_data,
            "version": 2,
            "updated_at": "2023-01-01T00:00:00Z",
        }

        mock_usersettings_port.update_settings.return_value = returned_data

        # Act
        result = await update_settings_use_case.execute(
            user_id=user_id, category=category, settings_data=settings_data, expected_version=expected_version
        )

        # Assert
        assert isinstance(result, UserSettings)
        assert result.user_id == user_id
        assert result.category == category
        assert result.data == settings_data
        assert result.version == 2

        mock_usersettings_port.update_settings.assert_called_once_with(
            user_id=user_id, category=category, data=settings_data, expected_version=expected_version
        )

    @pytest.mark.asyncio
    async def test_update_settings_without_version(self, update_settings_use_case, mock_usersettings_port):
        """Test settings update without expected version"""
        # Arrange
        user_id = "user-123"
        category = "notifications"
        settings_data = {"email": True, "push": False}

        returned_data = {
            "user_id": user_id,
            "category": category,
            "data": settings_data,
            "version": 1,
            "updated_at": "2023-01-01T00:00:00Z",
        }

        mock_usersettings_port.update_settings.return_value = returned_data

        # Act
        result = await update_settings_use_case.execute(user_id=user_id, category=category, settings_data=settings_data)

        # Assert
        assert isinstance(result, UserSettings)
        assert result.version == 1

        mock_usersettings_port.update_settings.assert_called_once_with(
            user_id=user_id, category=category, data=settings_data, expected_version=None
        )

    @pytest.mark.asyncio
    async def test_update_settings_failure(self, update_settings_use_case, mock_usersettings_port):
        """Test settings update failure"""
        # Arrange
        user_id = "user-123"
        category = "preferences"
        settings_data = {"theme": "dark"}
        expected_version = 1

        mock_usersettings_port.update_settings.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Failed to update settings"):
            await update_settings_use_case.execute(
                user_id=user_id, category=category, settings_data=settings_data, expected_version=expected_version
            )

    @pytest.mark.asyncio
    async def test_update_settings_port_exception(self, update_settings_use_case, mock_usersettings_port):
        """Test settings update port exception propagation"""
        # Arrange
        user_id = "user-123"
        category = "preferences"
        settings_data = {"theme": "dark"}

        mock_usersettings_port.update_settings.side_effect = Exception("Version conflict")

        # Act & Assert
        with pytest.raises(Exception, match="Version conflict"):
            await update_settings_use_case.execute(user_id=user_id, category=category, settings_data=settings_data)


class TestGetUserSettingsUseCase:
    """Test cases for GetUserSettings use case"""

    @pytest.fixture
    def mock_usersettings_port(self):
        """Mock UserSettings port"""
        return AsyncMock()

    @pytest.fixture
    def get_settings_use_case(self, mock_usersettings_port):
        """Create GetUserSettings use case instance"""
        return GetUserSettings(usersettings_port=mock_usersettings_port)

    @pytest.mark.asyncio
    async def test_get_specific_category_success(self, get_settings_use_case, mock_usersettings_port):
        """Test getting specific settings category"""
        # Arrange
        user_id = "user-123"
        category = "preferences"

        returned_data = {
            "user_id": user_id,
            "category": category,
            "data": {"theme": "dark", "language": "en"},
            "version": 1,
            "updated_at": "2023-01-01T00:00:00Z",
        }

        mock_usersettings_port.get_settings.return_value = returned_data

        # Act
        result = await get_settings_use_case.execute(user_id=user_id, category=category)

        # Assert
        assert isinstance(result, UserSettings)
        assert result.user_id == user_id
        assert result.category == category
        assert result.data == {"theme": "dark", "language": "en"}
        assert result.version == 1

        mock_usersettings_port.get_settings.assert_called_once_with(user_id, category)

    @pytest.mark.asyncio
    async def test_get_specific_category_not_found(self, get_settings_use_case, mock_usersettings_port):
        """Test getting non-existent settings category returns default"""
        # Arrange
        user_id = "user-123"
        category = "nonexistent"

        mock_usersettings_port.get_settings.return_value = None

        # Act
        result = await get_settings_use_case.execute(user_id=user_id, category=category)

        # Assert
        assert isinstance(result, UserSettings)
        assert result.user_id == user_id
        assert result.category == category
        assert result.data == {}
        assert result.version == 0

        mock_usersettings_port.get_settings.assert_called_once_with(user_id, category)

    @pytest.mark.asyncio
    async def test_get_all_settings_success(self, get_settings_use_case, mock_usersettings_port):
        """Test getting all user settings"""
        # Arrange
        user_id = "user-123"

        settings_list = [
            {
                "category": "preferences",
                "data": {"theme": "dark", "language": "en"},
                "version": 1,
                "updated_at": "2023-01-01T00:00:00Z",
            },
            {
                "category": "notifications",
                "data": {"email": True, "push": False},
                "version": 2,
                "updated_at": "2023-01-01T00:00:00Z",
            },
        ]

        mock_usersettings_port.get_all_settings.return_value = settings_list

        # Act
        result = await get_settings_use_case.execute(user_id=user_id)

        # Assert
        assert isinstance(result, UserSettingsCollection)
        assert result.user_id == user_id

        mock_usersettings_port.get_all_settings.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_get_all_settings_empty(self, get_settings_use_case, mock_usersettings_port):
        """Test getting all settings when none exist"""
        # Arrange
        user_id = "user-123"

        mock_usersettings_port.get_all_settings.return_value = []

        # Act
        result = await get_settings_use_case.execute(user_id=user_id)

        # Assert
        assert isinstance(result, UserSettingsCollection)
        assert result.user_id == user_id

        mock_usersettings_port.get_all_settings.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_get_settings_port_exception(self, get_settings_use_case, mock_usersettings_port):
        """Test port exception propagation"""
        # Arrange
        user_id = "user-123"
        category = "preferences"

        mock_usersettings_port.get_settings.side_effect = Exception("Service unavailable")

        # Act & Assert
        with pytest.raises(Exception, match="Service unavailable"):
            await get_settings_use_case.execute(user_id=user_id, category=category)
