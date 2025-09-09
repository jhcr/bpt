import os
from typing import Optional, List
from functools import lru_cache


class Config:
    """Base configuration class with environment variable helpers"""
    
    @staticmethod
    def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable with optional default"""
        return os.environ.get(key, default)
    
    @staticmethod
    def get_env_required(key: str) -> str:
        """Get required environment variable, raise if missing"""
        value = os.environ.get(key)
        if value is None:
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    @staticmethod
    def get_env_bool(key: str, default: bool = False) -> bool:
        """Get boolean environment variable"""
        value = os.environ.get(key, "").lower()
        return value in ("true", "1", "yes", "on") if value else default
    
    @staticmethod
    def get_env_int(key: str, default: Optional[int] = None) -> Optional[int]:
        """Get integer environment variable"""
        value = os.environ.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Environment variable {key} must be an integer, got: {value}")
    
    @staticmethod
    def get_env_list(key: str, separator: str = ",", default: Optional[List[str]] = None) -> List[str]:
        """Get list from environment variable"""
        value = os.environ.get(key)
        if value is None:
            return default or []
        return [item.strip() for item in value.split(separator) if item.strip()]


@lru_cache()
def get_common_config():
    """Get common configuration used across all services"""
    return {
        "env": Config.get_env("ENV", "development"),
        "debug": Config.get_env_bool("DEBUG", False),
        "aws_region": Config.get_env("AWS_REGION", "us-east-1"),
        "otel_service_name": Config.get_env("OTEL_SERVICE_NAME", "cloud-app"),
        "otel_endpoint": Config.get_env("OTEL_EXPORTER_OTLP_ENDPOINT"),
        "log_level": Config.get_env("LOG_LEVEL", "INFO"),
    }


@lru_cache()
def get_auth_config():
    """Get auth-related configuration"""
    return {
        "cognito_user_pool_id": Config.get_env("COGNITO_USER_POOL_ID"),
        "cognito_client_id": Config.get_env("COGNITO_CLIENT_ID"),
        "cognito_client_secret": Config.get_env("COGNITO_CLIENT_SECRET"),
        "jwks_url": Config.get_env("JWKS_URL"),
        "jwt_issuer": Config.get_env("JWT_ISSUER", "https://auth.example.com"),
        "jwt_audience": Config.get_env("JWT_AUDIENCE", "cloud-app"),
        "redis_url": Config.get_env_required("REDIS_URL"),
        "session_ttl": Config.get_env_int("SESSION_TTL_SECONDS", 1800),  # 30 min
        "access_token_ttl": Config.get_env_int("ACCESS_TOKEN_TTL_SECONDS", 900),  # 15 min
        "svc_token_ttl": Config.get_env_int("SVC_TOKEN_TTL_SECONDS", 300),  # 5 min
    }


@lru_cache()
def get_database_config():
    """Get database configuration"""
    return {
        "pg_dsn": Config.get_env("PG_DSN"),
        "redis_url": Config.get_env("REDIS_URL"),
        "dynamodb_endpoint_url": Config.get_env("DYNAMODB_ENDPOINT_URL"),
        "dynamodb_region": Config.get_env("AWS_REGION", "us-east-1"),
        "user_settings_table": Config.get_env("DYNAMODB_TABLE_USER_SETTINGS", "user_settings_dev"),
        "migrations_table": Config.get_env("USERSETTINGS_MIGRATIONS_TABLE", "usersettings_migrations_dev"),
    }


@lru_cache()
def get_kafka_config():
    """Get Kafka configuration"""
    return {
        "brokers": Config.get_env_list("KAFKA_BROKERS", default=["localhost:9092"]),
        "topic_prefix": Config.get_env("KAFKA_TOPIC_PREFIX", ""),
        "consumer_group_prefix": Config.get_env("KAFKA_CONSUMER_GROUP_PREFIX", "cloud-app"),
        "security_protocol": Config.get_env("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
        "sasl_mechanism": Config.get_env("KAFKA_SASL_MECHANISM"),
        "sasl_username": Config.get_env("KAFKA_SASL_USERNAME"),
        "sasl_password": Config.get_env("KAFKA_SASL_PASSWORD"),
    }


@lru_cache()
def get_service_urls():
    """Get service URL configuration"""
    return {
        "bff_url": Config.get_env("BFF_API_URL", "http://localhost:8080"),
        "auth_url": Config.get_env("AUTHSVC_URL", "http://localhost:8083"),
        "userprofiles_url": Config.get_env("USERPROFILES_URL", "http://localhost:8081"),
        "usersettings_url": Config.get_env("USERSETTINGS_URL", "http://localhost:8082"),
        "events_url": Config.get_env("EVENTS_URL", "http://localhost:8084"),
    }


def get_service_token_config(service_name: str):
    """Get service token configuration for a specific service"""
    service_key = service_name.replace("-", "_")
    return {
        "client_id": Config.get_env_required(f"SVC_CLIENT_ID_{service_key}"),
        "client_secret": Config.get_env_required(f"SVC_CLIENT_SECRET_{service_key}"),
        "sub_spn": f"spn:{service_name}",
        "scope": Config.get_env(f"SVC_SCOPE_{service_key}", f"svc.{service_name}.*"),
    }