# Assumptions:
# - Configuration management using environment variables
# - Pydantic Settings for validation
# - Default values for development environment


from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # Service
    service_name: str = "usersettings-service"
    service_port: int = 8082

    # DynamoDB
    dynamodb_table_user_settings: str = "user_settings_dev"
    dynamodb_endpoint_url: str | None = None
    dynamodb_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # Migrations
    usersettings_migrations_table: str = "usersettings_migrations_dev"

    # JWT & Auth
    jwt_issuer: str = "https://auth.example.com"
    jwt_audience: str = "internal"
    jwks_url: str = "https://auth.example.com/auth/.well-known/jwks.json"

    # OpenTelemetry
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "usersettings-service"
    otel_resource_attributes: str = "service.name=usersettings-service,service.version=1.0.0"

    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings singleton"""
    return Settings()
