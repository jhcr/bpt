# Assumptions:
# - Using pytest for testing framework
# - Testing HTTP client for UserSettings service
# - Mocking HTTP responses and error conditions

from unittest.mock import AsyncMock, Mock

import pytest
import structlog

from infrastructure.adapters.http_usersettings_client import HttpUserSettingsClient

# Mock the logger to avoid log output during tests
structlog.get_logger = Mock(return_value=Mock())


class TestHttpUserSettingsClient:
    """Test cases for HTTP UserSettings client"""

    @pytest.fixture
    def mock_service_token_client(self):
        """Mock ServiceTokenHttpClient"""
        return AsyncMock()

    @pytest.fixture
    def usersettings_client(self, mock_service_token_client):
        """Create HttpUserSettingsClient instance"""
        return HttpUserSettingsClient(service_token_client=mock_service_token_client)

    @pytest.mark.asyncio
    async def test_get_settings_success(self, usersettings_client, mock_service_token_client):
        """Test successful settings retrieval"""
        # Arrange
        user_id = "user-123"
        category = "preferences"
        expected_data = {
            "user_id": user_id,
            "category": category,
            "data": {"theme": "dark", "language": "en"},
            "version": 1,
            "updated_at": "2023-01-01T00:00:00Z",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_service_token_client.get.return_value = mock_response

        # Act
        result = await usersettings_client.get_settings(user_id, category)

        # Assert
        assert result == expected_data
        mock_service_token_client.get.assert_called_once_with(
            f"/internal/users/{user_id}/settings/{category}", actor_sub=user_id
        )

    @pytest.mark.asyncio
    async def test_get_settings_not_found(self, usersettings_client, mock_service_token_client):
        """Test settings not found"""
        # Arrange
        user_id = "user-123"
        category = "nonexistent"

        mock_response = Mock()
        mock_response.status_code = 404
        mock_service_token_client.get.return_value = mock_response

        # Act
        result = await usersettings_client.get_settings(user_id, category)

        # Assert
        assert result is None
        mock_service_token_client.get.assert_called_once_with(
            f"/internal/users/{user_id}/settings/{category}", actor_sub=user_id
        )

    @pytest.mark.asyncio
    async def test_get_all_settings_success(self, usersettings_client, mock_service_token_client):
        """Test successful retrieval of all settings"""
        # Arrange
        user_id = "user-123"
        expected_data = {
            "settings": [
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
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_service_token_client.get.return_value = mock_response

        # Act
        result = await usersettings_client.get_all_settings(user_id)

        # Assert
        assert result == expected_data["settings"]
        mock_service_token_client.get.assert_called_once_with(f"/internal/users/{user_id}/settings", actor_sub=user_id)

    @pytest.mark.asyncio
    async def test_get_all_settings_empty(self, usersettings_client, mock_service_token_client):
        """Test retrieval of all settings when none exist"""
        # Arrange
        user_id = "user-123"
        expected_data = {"settings": []}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_service_token_client.get.return_value = mock_response

        # Act
        result = await usersettings_client.get_all_settings(user_id)

        # Assert
        assert result == []
        mock_service_token_client.get.assert_called_once_with(f"/internal/users/{user_id}/settings", actor_sub=user_id)

    @pytest.mark.asyncio
    async def test_update_settings_success(self, usersettings_client, mock_service_token_client):
        """Test successful settings update"""
        # Arrange
        user_id = "user-123"
        category = "preferences"
        data = {"theme": "light", "language": "fr"}
        expected_version = 1

        expected_data = {
            "user_id": user_id,
            "category": category,
            "data": data,
            "version": 2,
            "updated_at": "2023-01-01T01:00:00Z",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_service_token_client.put.return_value = mock_response

        # Act
        result = await usersettings_client.update_settings(
            user_id=user_id, category=category, data=data, expected_version=expected_version
        )

        # Assert
        assert result == expected_data
        mock_service_token_client.put.assert_called_once_with(
            f"/internal/users/{user_id}/settings/{category}",
            json={"data": data, "expected_version": expected_version},
            actor_sub=user_id,
        )

    @pytest.mark.asyncio
    async def test_update_settings_without_version(self, usersettings_client, mock_service_token_client):
        """Test settings update without expected version"""
        # Arrange
        user_id = "user-123"
        category = "notifications"
        data = {"email": False, "push": True}

        expected_data = {
            "user_id": user_id,
            "category": category,
            "data": data,
            "version": 1,
            "updated_at": "2023-01-01T01:00:00Z",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_service_token_client.put.return_value = mock_response

        # Act
        result = await usersettings_client.update_settings(user_id=user_id, category=category, data=data)

        # Assert
        assert result == expected_data
        mock_service_token_client.put.assert_called_once_with(
            f"/internal/users/{user_id}/settings/{category}",
            json={"data": data, "expected_version": None},
            actor_sub=user_id,
        )

    @pytest.mark.asyncio
    async def test_update_settings_conflict(self, usersettings_client, mock_service_token_client):
        """Test settings update version conflict"""
        # Arrange
        user_id = "user-123"
        category = "preferences"
        data = {"theme": "dark"}
        expected_version = 1

        mock_response = Mock()
        mock_response.status_code = 409  # Conflict
        mock_service_token_client.put.return_value = mock_response

        # Act
        result = await usersettings_client.update_settings(
            user_id=user_id, category=category, data=data, expected_version=expected_version
        )

        # Assert
        assert result is None
        mock_service_token_client.put.assert_called_once_with(
            f"/internal/users/{user_id}/settings/{category}",
            json={"data": data, "expected_version": expected_version},
            actor_sub=user_id,
        )

    @pytest.mark.asyncio
    async def test_update_settings_http_error(self, usersettings_client, mock_service_token_client):
        """Test HTTP error during settings update"""
        # Arrange
        user_id = "user-123"
        category = "preferences"
        data = {"theme": "dark"}

        mock_service_token_client.put.side_effect = Exception("Network error")

        # Act & Assert
        with pytest.raises(Exception, match="Network error"):
            await usersettings_client.update_settings(user_id=user_id, category=category, data=data)

    @pytest.mark.asyncio
    async def test_get_settings_http_error(self, usersettings_client, mock_service_token_client):
        """Test HTTP error during settings retrieval"""
        # Arrange
        user_id = "user-123"
        category = "preferences"

        mock_service_token_client.get.side_effect = Exception("Service unavailable")

        # Act & Assert
        with pytest.raises(Exception, match="Service unavailable"):
            await usersettings_client.get_settings(user_id, category)
