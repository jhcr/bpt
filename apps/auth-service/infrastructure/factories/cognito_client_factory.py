"""Factory for creating Cognito client instances based on environment"""

import os

from application.ports.cognito_client import CognitoClient


class CognitoClientFactory:
    """Factory for creating Cognito client instances"""

    @staticmethod
    def create_client(
        user_pool_id: str, client_id: str, client_secret: str, region: str = "us-east-1"
    ) -> CognitoClient:
        """
        Create appropriate Cognito client based on environment

        Args:
            user_pool_id: Cognito User Pool ID
            client_id: Cognito Client ID
            client_secret: Cognito Client Secret
            region: AWS region

        Returns:
            CognitoClient: Instance of appropriate client
        """
        # Use mock client in development since Cognito is a Pro feature in LocalStack
        if os.getenv("ENV", "production") == "development":
            from infrastructure.adapters.mock.cognito_dev_mock import MockCognitoClientAdapter

            return MockCognitoClientAdapter(
                user_pool_id=user_pool_id,
                client_id=client_id,
                client_secret=client_secret,
                region=region,
            )
        else:
            from infrastructure.adapters.boto3.cognito_client import CognitoClientAdapter

            # Use localstack endpoint in production fallback
            endpoint_url = None
            if os.getenv("ENV", "production") == "development":
                endpoint_url = "http://localstack:4566"

            return CognitoClientAdapter(
                user_pool_id=user_pool_id,
                client_id=client_id,
                client_secret=client_secret,
                region=region,
                endpoint_url=endpoint_url,
            )
