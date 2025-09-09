#!/bin/bash
# Assumptions:
# - Running on Unix-like system with bash
# - Docker and docker-compose are installed
# - Python 3.12+ available
# - Node.js 18+ available for frontend

set -e

echo "🚀 Bootstrapping development environment..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required"; exit 1; }

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
fi

# Install pre-commit hooks
echo "🔧 Installing pre-commit hooks..."
pipx install pre-commit || pip install pre-commit
pre-commit install

# Start infrastructure services
echo "🐳 Starting infrastructure services..."
docker-compose -f docker-compose.dev.yml up -d postgres redis kafka localstack

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Create DynamoDB tables in LocalStack
echo "📊 Creating DynamoDB tables..."
aws --endpoint-url=http://localhost:4566 dynamodb create-table \
    --table-name user_settings_dev \
    --attribute-definitions AttributeName=user_id,AttributeType=S AttributeName=category,AttributeType=S \
    --key-schema AttributeName=user_id,KeyType=HASH AttributeName=category,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1 || true

aws --endpoint-url=http://localhost:4566 dynamodb create-table \
    --table-name usersettings_migrations_dev \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1 || true

# Create Kafka topics
echo "📨 Creating Kafka topics..."
docker exec bpt-kafka-1 kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --create --if-not-exists --topic user-events \
    --partitions 3 --replication-factor 1 || true

docker exec bpt-kafka-1 kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --create --if-not-exists --topic user-events-dlq \
    --partitions 1 --replication-factor 1 || true

echo "✅ Development environment ready!"
echo ""
echo "Next steps:"
echo "  make up    # Start all services"
echo "  make test  # Run tests"
echo "  make health # Check service health"