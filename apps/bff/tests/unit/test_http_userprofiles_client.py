# Assumptions:
# - Using pytest for testing framework
# - Testing HTTP client for UserProfiles service
# - Mocking HTTP responses and error conditions

from unittest.mock import AsyncMock, Mock

import pytest
import structlog

from infrastructure.adapters.http_userprofiles_client import HttpUserProfilesClient

# Mock the logger to avoid log output during tests
structlog.get_logger = Mock(return_value=Mock())


class TestHttpUserProfilesClient:
    """Test cases for HTTP UserProfiles client"""

    @pytest.fixture
    def mock_service_token_client(self):
        """Mock ServiceTokenHttpClient"""
        return AsyncMock()

    @pytest.fixture
    def userprofiles_client(self, mock_service_token_client):
        """Create HttpUserProfilesClient instance"""
        return HttpUserProfilesClient(service_token_client=mock_service_token_client)

    @pytest.mark.asyncio
    async def test_get_user_by_sub_success(self, userprofiles_client, mock_service_token_client):
        """Test successful user retrieval by Cognito subject"""
        # Arrange
        cognito_sub = "test-sub-123"
        expected_data = {
            "id": "user-uuid-123",
            "cognito_sub": cognito_sub,
            "email": "test@example.com",
            "display_name": "Test User",
            "avatar_url": "https://example.com/avatar.jpg",
            "phone": "+1234567890",
            "is_active": True,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_service_token_client.get.return_value = mock_response

        # Act
        result = await userprofiles_client.get_user_by_sub(cognito_sub)

        # Assert
        assert result == expected_data
        mock_service_token_client.get.assert_called_once_with(
            f"/internal/users/by-sub/{cognito_sub}", actor_sub=cognito_sub
        )

    @pytest.mark.asyncio
    async def test_get_user_by_sub_not_found(self, userprofiles_client, mock_service_token_client):
        """Test user not found by Cognito subject"""
        # Arrange
        cognito_sub = "nonexistent-sub"

        mock_response = Mock()
        mock_response.status_code = 404
        mock_service_token_client.get.return_value = mock_response

        # Act
        result = await userprofiles_client.get_user_by_sub(cognito_sub)

        # Assert
        assert result is None
        mock_service_token_client.get.assert_called_once_with(
            f"/internal/users/by-sub/{cognito_sub}", actor_sub=cognito_sub
        )

    @pytest.mark.asyncio
    async def test_get_user_by_sub_http_error(self, userprofiles_client, mock_service_token_client):
        """Test HTTP error during user retrieval by subject"""
        # Arrange
        cognito_sub = "test-sub-123"
        mock_service_token_client.get.side_effect = Exception("HTTP connection error")

        # Act & Assert
        with pytest.raises(Exception, match="HTTP connection error"):
            await userprofiles_client.get_user_by_sub(cognito_sub)

        mock_service_token_client.get.assert_called_once_with(
            f"/internal/users/by-sub/{cognito_sub}", actor_sub=cognito_sub
        )

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, userprofiles_client, mock_service_token_client):
        """Test successful user retrieval by internal ID"""
        # Arrange
        user_id = "user-uuid-123"
        expected_data = {
            "id": user_id,
            "cognito_sub": "test-sub-123",
            "email": "test@example.com",
            "display_name": "Test User",
            "avatar_url": None,
            "phone": None,
            "is_active": True,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_service_token_client.get.return_value = mock_response

        # Act
        result = await userprofiles_client.get_user_by_id(user_id)

        # Assert
        assert result == expected_data
        mock_service_token_client.get.assert_called_once_with(f"/internal/users/{user_id}")

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, userprofiles_client, mock_service_token_client):
        """Test user not found by internal ID"""
        # Arrange
        user_id = "nonexistent-uuid"

        mock_response = Mock()
        mock_response.status_code = 404
        mock_service_token_client.get.return_value = mock_response

        # Act
        result = await userprofiles_client.get_user_by_id(user_id)

        # Assert
        assert result is None
        mock_service_token_client.get.assert_called_once_with(f"/internal/users/{user_id}")

    @pytest.mark.asyncio
    async def test_get_user_by_id_http_error(self, userprofiles_client, mock_service_token_client):
        """Test HTTP error during user retrieval by ID"""
        # Arrange
        user_id = "user-uuid-123"
        mock_service_token_client.get.side_effect = Exception("Service unavailable")

        # Act & Assert
        with pytest.raises(Exception, match="Service unavailable"):
            await userprofiles_client.get_user_by_id(user_id)

        mock_service_token_client.get.assert_called_once_with(f"/internal/users/{user_id}")
