# Assumptions:
# - Using pytest for testing framework
# - Testing GetUser use case with mocked ports
# - Testing error handling and edge cases

from unittest.mock import AsyncMock, Mock

import pytest
import structlog

from application.use_cases.get_user import GetUser
from domain.entities.user import User

# Mock the logger to avoid log output during tests
structlog.get_logger = Mock(return_value=Mock())


class TestGetUserUseCase:
    """Test cases for GetUser use case"""

    @pytest.fixture
    def mock_userprofiles_port(self):
        """Mock UserProfiles port"""
        return AsyncMock()

    @pytest.fixture
    def mock_usersettings_port(self):
        """Mock UserSettings port"""
        return AsyncMock()

    @pytest.fixture
    def get_user_use_case(self, mock_userprofiles_port, mock_usersettings_port):
        """Create GetUser use case instance with mocked ports"""
        return GetUser(userprofiles_port=mock_userprofiles_port, usersettings_port=mock_usersettings_port)

    @pytest.mark.asyncio
    async def test_get_user_success_with_settings(
        self, get_user_use_case, mock_userprofiles_port, mock_usersettings_port
    ):
        """Test successful user retrieval with settings"""
        # Arrange
        user_sub = "test-sub-123"
        profile_data = {
            "id": "user-uuid-123",
            "cognito_sub": user_sub,
            "email": "test@example.com",
            "display_name": "Test User",
            "avatar_url": "https://example.com/avatar.jpg",
            "phone": "+1234567890",
            "is_active": True,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        settings_data = [
            {"category": "preferences", "data": {"theme": "dark", "language": "en"}, "version": 1},
            {"category": "notifications", "data": {"email": True, "push": False}, "version": 1},
        ]

        mock_userprofiles_port.get_user_by_sub.return_value = profile_data
        mock_usersettings_port.get_all_settings.return_value = settings_data

        # Act
        result = await get_user_use_case.execute(user_sub)

        # Assert
        assert isinstance(result, User)
        assert result.id == profile_data["id"]
        assert result.cognito_sub == user_sub
        assert result.email == profile_data["email"]
        assert result.display_name == profile_data["display_name"]

        # Verify port calls
        mock_userprofiles_port.get_user_by_sub.assert_called_once_with(user_sub)
        mock_usersettings_port.get_all_settings.assert_called_once_with(profile_data["id"])

    @pytest.mark.asyncio
    async def test_get_user_success_without_settings(
        self, get_user_use_case, mock_userprofiles_port, mock_usersettings_port
    ):
        """Test successful user retrieval without settings"""
        # Arrange
        user_sub = "test-sub-123"
        profile_data = {
            "id": "user-uuid-123",
            "cognito_sub": user_sub,
            "email": "test@example.com",
            "display_name": "Test User",
            "avatar_url": None,
            "phone": None,
            "is_active": True,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        mock_userprofiles_port.get_user_by_sub.return_value = profile_data
        mock_usersettings_port.get_all_settings.return_value = []

        # Act
        result = await get_user_use_case.execute(user_sub)

        # Assert
        assert isinstance(result, User)
        assert result.id == profile_data["id"]
        assert result.cognito_sub == user_sub
        mock_userprofiles_port.get_user_by_sub.assert_called_once_with(user_sub)
        mock_usersettings_port.get_all_settings.assert_called_once_with(profile_data["id"])

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self, get_user_use_case, mock_userprofiles_port, mock_usersettings_port):
        """Test user profile not found"""
        # Arrange
        user_sub = "nonexistent-sub"
        mock_userprofiles_port.get_user_by_sub.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="User not found"):
            await get_user_use_case.execute(user_sub)

        # Verify only profile port was called
        mock_userprofiles_port.get_user_by_sub.assert_called_once_with(user_sub)
        mock_usersettings_port.get_all_settings.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_settings_failure_continues(
        self, get_user_use_case, mock_userprofiles_port, mock_usersettings_port
    ):
        """Test that settings failure doesn't prevent user retrieval"""
        # Arrange
        user_sub = "test-sub-123"
        profile_data = {
            "id": "user-uuid-123",
            "cognito_sub": user_sub,
            "email": "test@example.com",
            "display_name": "Test User",
            "avatar_url": None,
            "phone": None,
            "is_active": True,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        mock_userprofiles_port.get_user_by_sub.return_value = profile_data
        mock_usersettings_port.get_all_settings.side_effect = Exception("Settings service down")

        # Act
        result = await get_user_use_case.execute(user_sub)

        # Assert - should still return user without settings
        assert isinstance(result, User)
        assert result.id == profile_data["id"]
        assert result.cognito_sub == user_sub

        # Verify both ports were called
        mock_userprofiles_port.get_user_by_sub.assert_called_once_with(user_sub)
        mock_usersettings_port.get_all_settings.assert_called_once_with(profile_data["id"])

    @pytest.mark.asyncio
    async def test_get_user_profile_service_failure(
        self, get_user_use_case, mock_userprofiles_port, mock_usersettings_port
    ):
        """Test profile service failure propagates"""
        # Arrange
        user_sub = "test-sub-123"
        mock_userprofiles_port.get_user_by_sub.side_effect = Exception("Profile service down")

        # Act & Assert
        with pytest.raises(Exception, match="Profile service down"):
            await get_user_use_case.execute(user_sub)

        # Verify only profile port was called
        mock_userprofiles_port.get_user_by_sub.assert_called_once_with(user_sub)
        mock_usersettings_port.get_all_settings.assert_not_called()
