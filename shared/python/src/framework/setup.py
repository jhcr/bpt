from setuptools import find_packages, setup

setup(
    name="bpt-shared",
    version="1.0.0",
    description="Shared library for BPT python microservices",
    author="BPT Team",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.13",
    install_requires=[
        # HTTP client dependencies
        "httpx>=0.25.0",
        # Logging dependencies
        "structlog>=23.2.0",
        "python-json-logger>=2.0.7",
        # Telemetry dependencies
        "opentelemetry-api>=1.28.0",
        "opentelemetry-sdk>=1.28.0",
        "opentelemetry-exporter-otlp-proto-grpc>=1.28.0",
        "opentelemetry-instrumentation-fastapi>=0.49b0",
        "opentelemetry-instrumentation-httpx>=0.49b0",
        "opentelemetry-instrumentation-boto3sqs>=0.49b0",
        "opentelemetry-instrumentation-psycopg>=0.49b0",
        # Auth dependencies
        "pyjwt[crypto]>=2.8.0",
        "cryptography>=41.0.0",
        # Config dependencies
        "pydantic>=2.10.0",
        "pydantic-settings>=2.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.23.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.13",
    ],
)
