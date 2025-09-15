# BPT (Building Platform Toolkit) - Complete System Design v1.0

**This document is code-generation ready for Claude Code**

This document captures the exact implementation state of the BPT microservices platform. Every component, API endpoint, database schema, and configuration described here reflects the actual working codebase.

## 1. Executive Summary

**Architecture**: Cloud-native microservices with Clean Architecture pattern
**Frontend**: React 18 + TypeScript + Vite SPA with Redux Toolkit + RTK Query
**Backend**: Python 3.12 + FastAPI microservices with Clean Architecture layering
**Authentication**: Custom session cipher + AWS Cognito + OAuth2 (Google/Facebook)
**Databases**: PostgreSQL (UserProfiles) + DynamoDB (UserSettings) + Redis (Sessions)
**Messaging**: Kafka for event streaming with DLQ and replay capabilities
**Infrastructure**: Docker Compose (dev) + Kubernetes/Istio (prod)

## 2. Current Implementation Status

### ✅ **Fully Implemented Services**
- **Auth Service**: Complete with session cipher, JWT, OAuth2, service tokens
- **BFF Service**: HTTP adapters, user composition, settings management
- **UserProfiles Service**: PostgreSQL with SQL functions, migration runner
- **UserSettings Service**: DynamoDB with OCC, migration system
- **Events Service**: Kafka producer/consumer with DLQ and replay
- **Frontend**: React SPA with custom auth UI, session cipher, OAuth buttons
- **Unit Tests**: Comprehensive test coverage for all services

### 🚧 **Infrastructure Status**
- ✅ Docker Compose development environment
- 🔄 Kubernetes manifests (base structure ready)
- 🔄 Terraform modules (EKS structure ready)

## 3. Directory Structure

```
BPT/
├── apps/                              # Microservices
│   ├── auth-service/                  # 50 Python files
│   │   ├── application/
│   │   │   ├── ports/                 # Interfaces
│   │   │   │   ├── cognito_client.py
│   │   │   │   ├── jwt_signer.py
│   │   │   │   ├── session_repository.py
│   │   │   │   └── user_repository.py
│   │   │   └── use_cases/             # Business logic
│   │   │       ├── create_cipher_session.py
│   │   │       ├── login_user.py
│   │   │       ├── oauth_callback.py
│   │   │       ├── register_user.py
│   │   │       ├── forgot_password.py
│   │   │       ├── logout_user.py
│   │   │       ├── refresh_token.py
│   │   │       └── svc_token.py
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   │   ├── session.py
│   │   │   │   ├── user.py
│   │   │   │   └── provider_entities.py
│   │   │   ├── services/
│   │   │   │   ├── auth_service.py
│   │   │   │   ├── response_mapper.py
│   │   │   │   ├── user_mapper.py
│   │   │   │   └── validation_service.py
│   │   │   ├── value_objects/
│   │   │   │   └── tokens.py
│   │   │   ├── errors.py
│   │   │   └── responses.py
│   │   ├── infrastructure/
│   │   │   ├── adapters/
│   │   │   │   ├── boto3/
│   │   │   │   │   └── cognito_client.py
│   │   │   │   ├── crypto/
│   │   │   │   │   ├── ecdh_kms.py
│   │   │   │   │   └── es256_signer.py
│   │   │   │   ├── mock/
│   │   │   │   │   └── cognito_dev_mock.py
│   │   │   │   └── redis/
│   │   │   │       └── session_repository.py
│   │   │   └── factories/
│   │   ├── presentation/
│   │   │   ├── api/
│   │   │   │   ├── auth_routes.py        # 14 endpoints
│   │   │   │   ├── jwks_routes.py        # 1 endpoint
│   │   │   │   └── svc_token_routes.py   # 1 endpoint
│   │   │   ├── middleware/
│   │   │   │   └── errors.py
│   │   │   ├── schema/
│   │   │   │   ├── auth_schemas.py
│   │   │   │   └── svc_token_schemas.py
│   │   │   └── app.py
│   │   ├── tests/unit/                   # Comprehensive tests
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   ├── bff/                              # 20 Python files
│   │   ├── application/
│   │   │   ├── ports/
│   │   │   │   ├── userprofiles_port.py
│   │   │   │   └── usersettings_port.py
│   │   │   └── use_cases/
│   │   │       ├── get_user.py
│   │   │       └── update_user_settings.py
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   │   └── user.py
│   │   │   └── responses.py
│   │   ├── infrastructure/
│   │   │   └── adapters/
│   │   │       ├── http_userprofiles_client.py
│   │   │       └── http_usersettings_client.py
│   │   ├── presentation/
│   │   │   ├── api/
│   │   │   │   └── user_routes.py        # 3 endpoints
│   │   │   ├── middleware/
│   │   │   │   ├── auth_jwt.py
│   │   │   │   └── errors.py
│   │   │   ├── schema/
│   │   │   │   └── user_schemas.py
│   │   │   └── app.py
│   │   ├── tests/unit/                   # Comprehensive tests
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   ├── events-service/                   # Event streaming
│   │   ├── application/
│   │   │   ├── ports/
│   │   │   │   ├── event_producer.py
│   │   │   │   ├── event_store.py
│   │   │   │   └── event_consumer.py
│   │   │   └── use_cases/
│   │   │       ├── publish_event.py
│   │   │       └── replay_events.py
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   │   └── event.py
│   │   │   ├── value_objects/
│   │   │   │   └── event_types.py
│   │   │   └── errors.py
│   │   ├── infrastructure/
│   │   │   ├── adapters/
│   │   │   │   ├── kafka/
│   │   │   │   │   └── kafka_producer.py
│   │   │   │   └── redis/
│   │   │   │       └── event_store.py
│   │   ├── presentation/
│   │   │   ├── api/
│   │   │   │   └── event_routes.py       # 6 endpoints
│   │   │   ├── middleware/
│   │   │   │   └── errors.py
│   │   │   ├── schema/
│   │   │   │   └── event_schemas.py
│   │   │   └── app.py
│   │   ├── tests/unit/                   # Comprehensive tests
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   ├── userprofiles-service/             # PostgreSQL service
│   │   ├── application/
│   │   │   ├── ports/
│   │   │   │   └── user_repository.py
│   │   │   └── use_cases/
│   │   │       ├── create_user.py
│   │   │       ├── get_user.py
│   │   │       └── update_user.py
│   │   ├── domain/
│   │   │   └── entities/
│   │   │       └── user.py
│   │   ├── infrastructure/
│   │   │   ├── adapters/
│   │   │   │   └── pg_user_repository.py
│   │   │   └── config/
│   │   ├── presentation/
│   │   │   ├── api/
│   │   │   │   ├── user_routes.py        # 6 endpoints
│   │   │   │   └── health_routes.py      # 3 endpoints
│   │   │   ├── schema/
│   │   │   │   └── user_schemas.py
│   │   │   └── app.py
│   │   ├── db/                           # Database structure
│   │   │   ├── functions/
│   │   │   │   └── users.sql             # CRUD functions
│   │   │   ├── init/
│   │   │   ├── procedures/
│   │   │   ├── sql/
│   │   │   └── tables/
│   │   │       └── users.sql             # Schema definition
│   │   ├── scripts/
│   │   │   └── run_pg_migrations.py      # Migration runner
│   │   ├── tests/unit/                   # Comprehensive tests
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   └── usersettings-service/             # DynamoDB service
│       ├── application/
│       │   ├── ports/
│       │   │   └── settings_repository.py
│       │   └── use_cases/
│       │       ├── get_settings.py
│       │       ├── update_settings.py
│       │       └── delete_settings.py
│       ├── domain/
│       │   └── entities/
│       │       └── user_setting.py
│       ├── infrastructure/
│       │   ├── adapters/
│       │   │   └── ddb_settings_repository.py
│       │   └── config/
│       ├── presentation/
│       │   ├── api/
│       │   │   ├── settings_routes.py    # 5 endpoints
│       │   │   └── health_routes.py      # 3 endpoints
│       │   ├── middleware/
│       │   │   └── auth_middleware.py
│       │   ├── schema/
│       │   │   └── settings_schemas.py
│       │   └── app.py
│       ├── db/
│       │   └── dynamodb/
│       │       └── migrations/           # DDB migration scripts
│       ├── scripts/
│       │   └── run_dynamodb_migrations.py
│       ├── tests/unit/                   # Comprehensive tests
│       ├── pyproject.toml
│       └── Dockerfile
│
├── frontend/                             # React frontend
│   └── web/
│       ├── src/
│       │   ├── components/
│       │   │   ├── AuthForm.tsx          # Login/signup with OAuth
│       │   │   └── Navigation.tsx
│       │   ├── lib/
│       │   │   └── sessionCipher.ts      # ECDH session encryption
│       │   ├── pages/
│       │   │   ├── Dashboard.tsx
│       │   │   ├── Settings.tsx
│       │   │   └── UserProfile.tsx
│       │   ├── store/
│       │   │   ├── api.ts                # RTK Query endpoints
│       │   │   ├── authSlice.ts          # Auth state
│       │   │   └── index.ts              # Store config
│       │   ├── App.tsx
│       │   └── main.tsx
│       ├── package.json
│       ├── vite.config.ts
│       └── Dockerfile.dev
│
├── shared/                               # Shared libraries
│   └── python/
│       └── src/
│           └── framework/
│               ├── auth/
│               │   ├── jwt_verify.py
│               │   ├── principals.py
│               │   └── service_tokens.py
│               ├── config/
│               │   └── env.py
│               ├── http/
│               │   └── client.py
│               ├── logging/
│               │   └── setup.py
│               └── telemetry/
│                   └── otel.py
│
├── infrastructure/                       # Infrastructure as Code
│   ├── kubernetes/
│   │   ├── base/
│   │   │   └── namespaces.yaml
│   │   ├── helm-charts/
│   │   │   └── cloud-app/
│   │   │       ├── Chart.yaml
│   │   │       ├── values.yaml
│   │   │       └── templates/
│   │   │           └── deployment.yaml
│   │   ├── istio/
│   │   │   ├── destination-rules.yaml
│   │   │   ├── gateway.yaml
│   │   │   └── security.yaml
│   │   └── monitoring/
│   │       ├── fluent-bit.yaml
│   │       └── otel-collector.yaml
│   ├── terraform/
│   │   ├── environments/
│   │   │   └── dev/
│   │   │       ├── main.tf
│   │   │       └── variables.tf
│   │   └── modules/
│   │       └── eks/
│   │           └── main.tf
│   └── localstack/
│
├── scripts/                             # Utility scripts
├── docker-compose.dev.yml              # Development environment
├── Makefile                            # Development workflows
├── .env.example                        # Environment template
├── .pre-commit-config.yaml            # Code quality
├── .importlinter                       # Architecture enforcement
└── README.md
```

## 4. Microservices Architecture

### 4.1 Service Overview

| Service | Port | Purpose | Database | Key Features |
|---------|------|---------|----------|-------------|
| **auth-service** | 8083 | Authentication & authorization | Redis | Session cipher, JWT, OAuth2, service tokens |
| **bff** | 8080 | Backend for Frontend | None | API composition, service token client |
| **userprofiles-service** | 8081 | User profile management | PostgreSQL | SQL functions, migration runner |
| **usersettings-service** | 8082 | User settings & preferences | DynamoDB | OCC, migration registry |
| **events-service** | 8084 | Event streaming | Kafka + Redis | DLQ, replay, batch processing |
| **frontend** | 3000 | React SPA | - | Session cipher, OAuth UI |

### 4.2 Clean Architecture Implementation

Each service follows strict Clean Architecture with layers:

```
presentation/     # FastAPI routes, Pydantic schemas, middleware
    api/         # Route handlers
    middleware/  # Auth, error handling, CORS
    schema/      # Request/response models
    app.py       # FastAPI application factory

application/     # Use cases and ports (interfaces)
    use_cases/   # Business orchestration
    ports/       # Abstract interfaces

domain/          # Business logic (pure Python)
    entities/    # Domain objects
    services/    # Domain services
    value_objects/  # Value objects
    errors.py    # Domain exceptions

infrastructure/  # External concerns
    adapters/    # Database, HTTP, crypto implementations
    config/      # Configuration and DI
    telemetry/   # Logging and tracing

tests/          # Unit, integration, e2e tests
    unit/       # Domain and application tests
```

## 5. Authentication System

### 5.1 Session Cipher (ECDH + HKDF + AES-GCM)

**Password Protection Flow:**
1. Client requests session: `POST /auth/session`
2. Server generates ECDH keypair, returns public key + session ID
3. Client encrypts password using WebCrypto ECDH + HKDF + AES-GCM
4. Client sends encrypted payload: `POST /auth/login`
5. Server decrypts using stored private key

**Implementation Files:**
- Backend: `apps/auth-service/infrastructure/adapters/crypto/ecdh_kms.py`
- Frontend: `frontend/web/src/lib/sessionCipher.ts`

### 5.2 JWT Token System

**ES256 Signed JWTs with first-party claims:**
```json
{
  "iss": "https://auth.example.com",
  "sub": "3f88...c012",
  "aud": "cloud-app",
  "iat": 1757419200,
  "exp": 1757420100,
  "jti": "a2c3...9f21",
  "sid": "1b0b...3444",
  "sidv": 3,
  "roles": ["user"],
  "scope": "user.read usersettings.read usersettings.write",
  "idp": "cognito"
}
```

**Token Flow:**
- Access tokens: 15-minute expiry, stored in memory only
- Refresh tokens: Server-side in Redis, tied to httpOnly cookie
- JWKS endpoint: `GET /.well-known/jwks.json`

### 5.3 OAuth2 Integration

**Supported Providers:** Google, Facebook (via AWS Cognito)

**OAuth Endpoints:**
- `GET /auth/social/providers` - List available providers
- `GET /auth/social/{provider}/authorize` - Get authorization URL
- `GET /auth/callback` - Handle OAuth callback

**Frontend OAuth Flow:**
```typescript
const handleOAuthLogin = async (provider: string) => {
  const response = await fetch(`/auth/social/${provider}/authorize`);
  const data = await response.json();
  window.location.href = data.authorization_url;
};
```

### 5.4 Service Token System

**Inter-service authentication with actor claims:**
```json
{
  "iss": "https://auth.example.com",
  "sub": "spn:bff",
  "aud": "internal",
  "token_use": "svc",
  "scope": "svc.userprofiles.read svc.usersettings.write",
  "act": {
    "sub": "user-uuid",
    "scope": "user.read usersettings.write",
    "roles": ["user"]
  }
}
```

**Service Token Endpoint:**
- `POST /auth/svc/token` - Issue service tokens with client credentials

## 6. API Specifications

### 6.1 Auth Service API (16 endpoints)

**Session Management:**
- `POST /auth/session` - Create cipher session
- `POST /auth/login` - Login with encrypted password
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout and invalidate session

**User Registration:**
- `POST /auth/signup` - Register new user
- `POST /auth/confirm-signup` - Confirm with verification code
- `POST /auth/resend-confirmation` - Resend confirmation code

**Password Reset:**
- `POST /auth/forgot-password` - Initiate password reset
- `POST /auth/confirm-forgot-password` - Confirm new password

**OAuth2:**
- `GET /auth/social/providers` - List OAuth providers
- `GET /auth/social/{provider}/authorize` - Get OAuth URL
- `GET /auth/callback` - Handle OAuth callback

**Service Tokens:**
- `POST /auth/svc/token` - Issue inter-service tokens

**JWKS:**
- `GET /.well-known/jwks.json` - JWT public keys

**Token Exchange:**
- `POST /auth/token` - Exchange codes for tokens

### 6.2 BFF API (3 endpoints)

**User Management:**
- `GET /api/v1/user` - Get current user profile with settings
- `GET /api/v1/user/settings` - Get user settings by category
- `PUT /api/v1/user/settings/{category}` - Update user settings

### 6.3 UserProfiles Service API (9 endpoints)

**Public Routes:**
- `GET /users/{user_id}` - Get user by ID
- `GET /users/cognito/{cognito_sub}` - Get user by Cognito subject
- `GET /users` - List users (paginated)
- `POST /users` - Create new user
- `PUT /users/{user_id}` - Update user

**Health Checks:**
- `GET /health` - General health
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

### 6.4 UserSettings Service API (8 endpoints)

**Settings Management:**
- `GET /settings/user/{user_id}` - Get all user settings
- `GET /settings/user/{user_id}/category/{category}` - Get settings by category
- `PUT /settings/user/{user_id}/category/{category}` - Update settings
- `DELETE /settings/user/{user_id}/category/{category}` - Delete category
- `DELETE /settings/user/{user_id}` - Delete all user settings

**Health Checks:**
- `GET /health` - General health
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

### 6.5 Events Service API (6 endpoints)

**Event Publishing:**
- `POST /publish` - Publish single event
- `POST /publish/batch` - Publish multiple events

**Event Replay:**
- `POST /replay` - Replay events by time range
- `POST /replay/dlq` - Replay DLQ events
- `GET /replay/preview` - Preview replay events

**Health:**
- `GET /health` - Health check

## 7. Database Schemas

### 7.1 PostgreSQL (UserProfiles)

**Schema: `userprofiles.users`**
```sql
CREATE TABLE userprofiles.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_sub TEXT UNIQUE NOT NULL,
    email CITEXT UNIQUE NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    phone TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_email ON userprofiles.users(email);
CREATE INDEX idx_users_cognito_sub ON userprofiles.users(cognito_sub);
CREATE INDEX idx_users_active ON userprofiles.users(is_active) WHERE is_active = true;
CREATE INDEX idx_users_created_at ON userprofiles.users(created_at);

-- Auto-update trigger
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON userprofiles.users
    FOR EACH ROW
    EXECUTE FUNCTION userprofiles.update_updated_at_column();
```

**SQL Functions (CRUD):**
- `userprofiles.create_user()` - Returns full row
- `userprofiles.get_user_by_id()` - Single user lookup
- `userprofiles.get_user_by_sub()` - Cognito subject lookup
- `userprofiles.get_user_by_email()` - Email lookup
- `userprofiles.update_user()` - Update with COALESCE
- `userprofiles.delete_user()` - Hard delete, returns boolean
- `userprofiles.soft_delete_user()` - Soft delete, returns boolean

**Migration System:**
- Runner: `apps/userprofiles-service/scripts/run_pg_migrations.py`
- Order: init → tables → sql → functions → procedures
- Tracking: `userprofiles.schema_migrations` table

### 7.2 DynamoDB (UserSettings)

**Table: `user_settings_{env}`**
```json
{
  "TableName": "user_settings_dev",
  "KeySchema": [
    {"AttributeName": "user_id", "KeyType": "HASH"},
    {"AttributeName": "category", "KeyType": "RANGE"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "user_id", "AttributeType": "S"},
    {"AttributeName": "category", "AttributeType": "S"}
  ],
  "BillingMode": "PAY_PER_REQUEST",
  "TimeToLiveSpecification": {
    "AttributeName": "ttl_epoch_s",
    "Enabled": true
  },
  "PointInTimeRecoverySpecification": {"PointInTimeRecoveryEnabled": true},
  "SSESpecification": {"SSEEnabled": true}
}
```

**Item Structure:**
```json
{
  "user_id": "uuid",
  "category": "preferences|notifications|privacy",
  "data": {
    "theme": "dark",
    "language": "en",
    "timezone": "UTC"
  },
  "version": 1,
  "updated_at": "2023-09-14T12:00:00Z",
  "ttl_epoch_s": 1693824000
}
```

**Optimistic Concurrency Control:**
```python
def put_with_occ(self, user_id: str, category: str, data: dict, expected_version: int|None):
    expr = "SET #d=:d, #u=:u, #v = if_not_exists(#v, :zero) + :one"
    cond = "attribute_not_exists(#v)" if expected_version is None else "#v = :ev"
    # ConditionalCheckFailedException on version mismatch
```

**Migration System:**
- Registry: `usersettings_migrations_{env}` table
- Runner: `apps/usersettings-service/scripts/run_dynamodb_migrations.py`
- Format: Python modules with `up(ddb)` function

### 7.3 Redis (Sessions)

**Session Storage:**
```json
{
  "sid:1b0b...3444": {
    "user_id": "uuid",
    "cognito_sub": "cognito-sub",
    "refresh_token": "cognito-refresh-token",
    "version": 3,
    "created_at": "2023-09-14T12:00:00Z",
    "expires_at": "2023-09-14T12:30:00Z"
  }
}
```

**Cipher Session Storage:**
```json
{
  "cipher:session-id": {
    "server_private_key_pem": "-----BEGIN PRIVATE KEY-----...",
    "server_public_key_jwk": {...},
    "created_at": "2023-09-14T12:00:00Z"
  }
}
```

## 8. Event System (Kafka)

### 8.1 Event Schema

**Event Envelope:**
```json
{
  "event_id": "uuid",
  "event_type": "user.created.v1",
  "user_id": "uuid",
  "timestamp": "2023-09-14T12:00:00Z",
  "payload": {
    "email": "user@example.com",
    "display_name": "User Name"
  },
  "metadata": {
    "version": 1,
    "source": "userprofiles-service",
    "correlation_id": "corr-123",
    "trace_id": "trace-456"
  },
  "source": "userprofiles-service",
  "correlation_id": "corr-123",
  "trace_id": "trace-456"
}
```

### 8.2 Event Types

**Defined in `domain/value_objects/event_types.py`:**
```python
class EventType(Enum):
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    SETTINGS_UPDATED = "settings.updated"

class TopicName(Enum):
    USER_EVENTS = "user-events"
    SYSTEM_EVENTS = "system-events"
    DLQ_EVENTS = "dlq-events"
    TEST_EVENTS = "test-events"

EVENT_TOPIC_MAPPING = {
    EventType.USER_CREATED: TopicName.USER_EVENTS,
    EventType.USER_UPDATED: TopicName.USER_EVENTS,
    EventType.USER_DELETED: TopicName.USER_EVENTS,
    EventType.SETTINGS_UPDATED: TopicName.SYSTEM_EVENTS,
}
```

### 8.3 Event Operations

**Publishing (Single):**
```python
await publish_use_case.execute(
    event_type=EventType.USER_CREATED,
    payload={"email": "user@example.com"},
    user_id="user-123",
    correlation_id="corr-123",
    trace_id="trace-456",
    source="userprofiles-service"
)
```

**Publishing (Batch):**
```python
events_data = [
    {
        "event_type": "user.created",
        "payload": {"email": "user1@example.com"},
        "user_id": "user-123",
        "source": "auth-service"
    },
    {
        "event_type": "user.updated",
        "payload": {"changes": ["email"]},
        "user_id": "user-456",
        "source": "user-service"
    }
]
await publish_use_case.execute_batch(events_data)
```

**Event Replay:**
```python
await replay_use_case.execute(
    from_timestamp=datetime(2023, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
    to_timestamp=datetime(2023, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
    event_types=[EventType.USER_CREATED, EventType.USER_UPDATED],
    user_id="user-123",  # Optional filter
    target_topic=TopicName.TEST_EVENTS,  # Optional override
    dry_run=False
)
```

**DLQ Replay:**
```python
await replay_use_case.replay_dlq_events(
    dlq_topic=TopicName.DLQ_EVENTS,
    target_topic=TopicName.USER_EVENTS,
    max_events=50
)
```

### 8.4 DLQ Structure

**DLQ Message Format:**
```json
{
  "original_event": {
    "event_id": "uuid",
    "event_type": "user.created",
    // ... original event data
  },
  "failure_reason": "Kafka publish failed: Broker not available",
  "failure_timestamp": "2023-09-14T12:00:00Z",
  "retry_count": 3,
  "original_topic": "user-events"
}
```

## 9. Frontend Implementation

### 9.1 Technology Stack

**Core:**
- React 18.2.0 with TypeScript
- Vite 5.0.0 build tool
- React Router DOM 6.20.0

**State Management:**
- Redux Toolkit 2.0.0
- RTK Query for API calls
- React Redux 9.0.0

**HTTP Client:**
- Axios 1.6.0 for custom requests
- RTK Query baseQuery for API

### 9.2 Session Cipher Implementation

**WebCrypto ECDH + HKDF + AES-GCM:**
```typescript
// frontend/web/src/lib/sessionCipher.ts
export async function encryptPassword({
  serverPublicKeyJwk,
  sid,
  password
}: {
  serverPublicKeyJwk: JsonWebKey;
  sid: string;
  password: string;
}) {
  // Generate client ECDH keypair
  const clientKey = await crypto.subtle.generateKey(
    { name: "ECDH", namedCurve: "P-256" },
    true,
    ["deriveBits"]
  );

  // Import server public key
  const serverKey = await crypto.subtle.importKey(
    "jwk",
    serverPublicKeyJwk,
    { name: "ECDH", namedCurve: "P-256" },
    true,
    []
  );

  // ECDH key exchange
  const secretBits = await crypto.subtle.deriveBits(
    { name: "ECDH", public: serverKey },
    clientKey.privateKey,
    256
  );

  // HKDF key derivation
  const hkdfKey = await crypto.subtle.importKey(
    "raw",
    secretBits,
    "HKDF",
    false,
    ["deriveKey"]
  );

  const aeadKey = await crypto.subtle.deriveKey(
    {
      name: "HKDF",
      hash: "SHA-256",
      salt: new TextEncoder().encode(sid),
      info: new TextEncoder().encode("pwd-login-v1")
    },
    hkdfKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt"]
  );

  // AES-GCM encryption
  const nonce = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await crypto.subtle.encrypt(
    {
      name: "AES-GCM",
      iv: nonce,
      additionalData: new TextEncoder().encode(sid)
    },
    aeadKey,
    new TextEncoder().encode(password)
  );

  // Export client public key
  const clientPublicKeyJwk = await crypto.subtle.exportKey("jwk", clientKey.publicKey);

  return {
    client_public_key_jwk: clientPublicKeyJwk,
    nonce: base64urlEncode(nonce),
    password_enc: base64urlEncode(new Uint8Array(ciphertext))
  };
}
```

### 9.3 OAuth Implementation

**OAuth Button Handlers:**
```typescript
// frontend/web/src/components/AuthForm.tsx
const handleOAuthLogin = async (provider: string) => {
  try {
    setIsLoading(true);
    const currentUrl = window.location.href;

    const response = await fetch(
      `/auth/social/${provider}/authorize?redirect_after_login=${encodeURIComponent(currentUrl)}`
    );

    if (!response.ok) {
      throw new Error('Failed to get authorization URL');
    }

    const data = await response.json();
    window.location.href = data.authorization_url;
  } catch (error) {
    console.error(`${provider} OAuth error:`, error);
    setErrors({ general: `Failed to connect with ${provider}. Please try again.` });
    setIsLoading(false);
  }
};

// Button implementations
<button
  type="button"
  className="social-btn google-btn"
  disabled={isLoading}
  onClick={() => handleOAuthLogin('google')}
>
  <span>Continue with Google</span>
</button>

<button
  type="button"
  className="social-btn facebook-btn"
  disabled={isLoading}
  onClick={() => handleOAuthLogin('facebook')}
>
  <span>Continue with Facebook</span>
</button>
```

### 9.4 RTK Query API Integration

**API Client Configuration:**
```typescript
// frontend/web/src/store/api.ts
const baseQuery = fetchBaseQuery({
  baseUrl: '/',
  credentials: 'include', // Include httpOnly cookies
  prepareHeaders: (headers, { getState }) => {
    const token = (getState() as RootState).auth.accessToken;
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    headers.set('Content-Type', 'application/json');
    return headers;
  },
});

export const api = createApi({
  reducerPath: 'api',
  baseQuery,
  tagTypes: ['User', 'Settings'],
  endpoints: (builder) => ({
    // Authentication
    createSession: builder.mutation<SessionResponse, void>({
      query: () => ({ url: '/auth/session', method: 'POST', body: {} }),
    }),

    login: builder.mutation<LoginResponse, LoginRequest>({
      query: (credentials) => ({
        url: '/auth/login',
        method: 'POST',
        body: credentials,
      }),
    }),

    // OAuth
    getSocialProviders: builder.query<SocialProvidersResponse, void>({
      query: () => '/auth/social/providers',
    }),

    getOAuthAuthorizeUrl: builder.query<OAuthAuthorizeResponse, { provider: string; redirectAfterLogin?: string }>({
      query: ({ provider, redirectAfterLogin }) => ({
        url: `/auth/social/${provider}/authorize`,
        params: redirectAfterLogin ? { redirect_after_login: redirectAfterLogin } : undefined,
      }),
    }),

    // User management
    getCurrentUser: builder.query<User, void>({
      query: () => '/api/v1/user',
      providesTags: ['User'],
    }),

    // User settings
    getUserSettings: builder.query<any, { category?: string }>({
      query: ({ category }) => ({
        url: '/api/v1/user/settings',
        params: category ? { category } : undefined,
      }),
      providesTags: ['Settings'],
    }),

    updateUserSettings: builder.mutation<any, { category: string; data: any; expectedVersion?: number }>({
      query: ({ category, data, expectedVersion }) => ({
        url: `/api/v1/user/settings/${category}`,
        method: 'PUT',
        body: { data, expected_version: expectedVersion },
      }),
      invalidatesTags: ['Settings', 'User'],
    }),
  }),
});
```

## 10. Infrastructure & Deployment

### 10.1 Docker Compose (Development)

**Services Configuration:**
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports: ["5432:5432"]
    volumes: ["postgres_data:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    command: redis-server --appendonly yes
    volumes: ["redis_data:/data"]

  kafka:
    image: bitnami/kafka:3.6
    ports: ["9092:9092"]
    environment:
      KAFKA_ENABLE_KRAFT: "yes"
      KAFKA_CFG_PROCESS_ROLES: broker,controller
      KAFKA_CFG_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CFG_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093
      KAFKA_CFG_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
    volumes: ["kafka_data:/bitnami/kafka"]

  localstack:
    image: localstack/localstack:3.0
    ports: ["4566:4566"]
    environment:
      SERVICES: dynamodb,s3,secretsmanager
      DEBUG: 1
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock"
      - "localstack_data:/var/lib/localstack"

  # Microservices
  auth-service:
    build:
      context: .
      dockerfile: apps/auth-service/Dockerfile
    ports: ["8083:8083"]
    environment:
      - ENV=development
      - REDIS_URL=redis://redis:6379/0
      - PG_DSN=postgresql://postgres:password@postgres:5432/appdb
    depends_on: [redis, postgres]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8083/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  bff:
    build:
      context: .
      dockerfile: apps/bff/Dockerfile
    ports: ["8080:8080"]
    environment:
      - ENV=development
      - USERPROFILES_URL=http://userprofiles-service:8081
      - USERSETTINGS_URL=http://usersettings-service:8082
      - AUTH_SERVICE_URL=http://auth-service:8083
    depends_on: [auth-service, userprofiles-service, usersettings-service]

  userprofiles-service:
    build:
      context: .
      dockerfile: apps/userprofiles-service/Dockerfile
    ports: ["8081:8081"]
    environment:
      - ENV=development
      - PG_DSN=postgresql://postgres:password@postgres:5432/appdb
    depends_on: [postgres]

  usersettings-service:
    build:
      context: .
      dockerfile: apps/usersettings-service/Dockerfile
    ports: ["8082:8082"]
    environment:
      - ENV=development
      - DYNAMODB_ENDPOINT_URL=http://localstack:4566
      - DYNAMODB_TABLE_USER_SETTINGS=user_settings_dev
    depends_on: [localstack]

  events-service:
    build:
      context: .
      dockerfile: apps/events-service/Dockerfile
    ports: ["8084:8084"]
    environment:
      - ENV=development
      - KAFKA_BROKERS=kafka:9092
      - REDIS_URL=redis://redis:6379/1
    depends_on: [kafka, redis]

  frontend:
    build:
      context: frontend/web
      dockerfile: Dockerfile.dev
    ports: ["3000:3000"]
    volumes: ["./frontend/web:/app", "/app/node_modules"]
    environment:
      - VITE_API_URL=http://localhost:8080

volumes:
  postgres_data:
  redis_data:
  kafka_data:
  localstack_data:
```

### 10.2 Service Dockerfiles

**Standard Service Dockerfile:**
```dockerfile
# apps/*/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv

# Copy shared dependencies
COPY shared/python/pyproject.toml ./opt/shared/pyproject.toml
COPY shared/python/src ./opt/shared/src
RUN uv pip install -e ./opt/shared --system

# Copy service dependencies
COPY apps/{service}/pyproject.toml ./
RUN uv pip install --system --no-cache-dir -e .

# Copy application code
COPY apps/{service}/ ./

# Create startup script
RUN echo '#!/bin/bash\nexport PYTHONPATH=/app\ncd /app\nexec python -m uvicorn presentation.app:app --host 0.0.0.0 --port 808X' > /start.sh && chmod +x /start.sh

EXPOSE 808X
CMD ["/start.sh"]
```

### 10.3 Kubernetes Configuration

**Namespace:**
```yaml
# infrastructure/kubernetes/base/namespaces.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bpt-prod
  labels:
    istio-injection: enabled
```

**Helm Chart Structure:**
```yaml
# infrastructure/kubernetes/helm-charts/cloud-app/Chart.yaml
apiVersion: v2
name: cloud-app
description: BPT Cloud Application
type: application
version: 0.1.0
appVersion: "1.0"

# infrastructure/kubernetes/helm-charts/cloud-app/values.yaml
global:
  environment: prod
  imageRegistry: your-registry
  imagePullPolicy: IfNotPresent

services:
  auth-service:
    replicaCount: 2
    image:
      repository: bpt-auth-service
      tag: latest
    service:
      port: 8083
    env:
      ENV: production
      REDIS_URL: redis://redis-service:6379/0

  bff:
    replicaCount: 3
    image:
      repository: bpt-bff
      tag: latest
    service:
      port: 8080

  # ... other services
```

**Service Deployment Template:**
```yaml
# infrastructure/kubernetes/helm-charts/cloud-app/templates/deployment.yaml
{{- range $service, $config := .Values.services }}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ $service }}
  namespace: {{ $.Values.global.namespace | default "bpt-prod" }}
  labels:
    app: {{ $service }}
    version: {{ $config.image.tag }}
spec:
  replicas: {{ $config.replicaCount }}
  selector:
    matchLabels:
      app: {{ $service }}
  template:
    metadata:
      labels:
        app: {{ $service }}
        version: {{ $config.image.tag }}
    spec:
      containers:
      - name: {{ $service }}
        image: {{ $.Values.global.imageRegistry }}/{{ $config.image.repository }}:{{ $config.image.tag }}
        imagePullPolicy: {{ $.Values.global.imagePullPolicy }}
        ports:
        - containerPort: {{ $config.service.port }}
        env:
        {{- range $key, $value := $config.env }}
        - name: {{ $key }}
          value: {{ $value | quote }}
        {{- end }}
        livenessProbe:
          httpGet:
            path: /health/live
            port: {{ $config.service.port }}
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: {{ $config.service.port }}
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: {{ $service }}
  namespace: {{ $.Values.global.namespace | default "bpt-prod" }}
  labels:
    app: {{ $service }}
spec:
  selector:
    app: {{ $service }}
  ports:
  - port: {{ $config.service.port }}
    targetPort: {{ $config.service.port }}
    protocol: TCP
{{- end }}
```

### 10.4 Istio Configuration

**Gateway:**
```yaml
# infrastructure/kubernetes/istio/gateway.yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: bpt-gateway
  namespace: bpt-prod
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - api.example.com
    tls:
      httpsRedirect: true
  - port:
      number: 443
      name: https
      protocol: HTTPS
    hosts:
    - api.example.com
    tls:
      mode: SIMPLE
      credentialName: bpt-tls-cert

---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: bff-vs
  namespace: bpt-prod
spec:
  hosts:
  - api.example.com
  gateways:
  - bpt-gateway
  http:
  - match:
    - uri:
        prefix: "/api/"
    timeout: 2s
    retries:
      attempts: 3
      perTryTimeout: 600ms
      retryOn: "5xx,connect-failure,refused-stream"
    route:
    - destination:
        host: bff.bpt-prod.svc.cluster.local
        port:
          number: 8080
  - match:
    - uri:
        prefix: "/auth/"
    route:
    - destination:
        host: auth-service.bpt-prod.svc.cluster.local
        port:
          number: 8083
```

**Security Policies:**
```yaml
# infrastructure/kubernetes/istio/security.yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default-strict
  namespace: bpt-prod
spec:
  mtls:
    mode: STRICT

---
apiVersion: security.istio.io/v1beta1
kind: RequestAuthentication
metadata:
  name: bpt-jwt
  namespace: bpt-prod
spec:
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/auth/.well-known/jwks.json"
    forwardOriginalToken: true

---
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: bff-user-access
  namespace: bpt-prod
spec:
  selector:
    matchLabels:
      app: bff
  rules:
  - to:
    - operation:
        paths: ["/api/v1/user*"]
    when:
    - key: request.auth.claims[scope]
      values: ["*user.read*"]
```

**Destination Rules:**
```yaml
# infrastructure/kubernetes/istio/destination-rules.yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: bff-dr
  namespace: bpt-prod
spec:
  host: bff.bpt-prod.svc.cluster.local
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
    outlierDetection:
      consecutiveErrors: 3
      interval: 30s
      baseEjectionTime: 30s
    circuitBreaker:
      connectionPool:
        tcp:
          maxConnections: 100
        http:
          http1MaxPendingRequests: 10
          maxRequestsPerConnection: 2

---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: auth-service-dr
  namespace: bpt-prod
spec:
  host: auth-service.bpt-prod.svc.cluster.local
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
    outlierDetection:
      consecutiveErrors: 5
      interval: 60s
      baseEjectionTime: 60s
```

### 10.5 Terraform Infrastructure

**EKS Module:**
```hcl
# infrastructure/terraform/modules/eks/main.tf
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.public_access_cidrs
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy,
  ]

  tags = var.tags
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.cluster_name}-workers"
  node_role_arn   = aws_iam_role.worker.arn
  subnet_ids      = var.private_subnet_ids

  scaling_config {
    desired_size = var.node_desired_capacity
    max_size     = var.node_max_capacity
    min_size     = var.node_min_capacity
  }

  instance_types = var.node_instance_types
  capacity_type  = var.node_capacity_type

  depends_on = [
    aws_iam_role_policy_attachment.worker_AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.worker_AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.worker_AmazonEC2ContainerRegistryReadOnly,
  ]

  tags = var.tags
}
```

**Environment Configuration:**
```hcl
# infrastructure/terraform/environments/dev/main.tf
terraform {
  required_version = ">= 1.0"

  backend "s3" {
    bucket = "bpt-terraform-state"
    key    = "dev/terraform.tfstate"
    region = "us-east-1"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "dev"
      Project     = "bpt"
      ManagedBy   = "terraform"
    }
  }
}

module "eks" {
  source = "../../modules/eks"

  cluster_name           = "bpt-dev"
  kubernetes_version     = "1.28"
  node_instance_types    = ["t3.medium"]
  node_desired_capacity  = 2
  node_min_capacity      = 1
  node_max_capacity      = 5

  subnet_ids         = data.aws_subnets.all.ids
  private_subnet_ids = data.aws_subnets.private.ids

  tags = {
    Environment = "dev"
  }
}
```

## 11. Testing Strategy

### 11.1 Unit Tests Coverage

**Test Structure per Service:**
```
tests/
└── unit/
    ├── test_use_cases/         # Application layer tests
    ├── test_adapters/          # Infrastructure tests
    ├── test_entities/          # Domain model tests
    ├── test_routes/            # API endpoint tests
    └── test_middleware/        # Middleware tests
```

**Example Test Implementation:**
```python
# apps/auth-service/tests/unit/test_login_use_case.py
import pytest
from unittest.mock import AsyncMock, Mock

from application.use_cases.login_user import LoginUserUseCase
from domain.entities.user import User
from domain.errors import AuthenticationError

class TestLoginUserUseCase:
    @pytest.fixture
    def mock_cognito_client(self):
        return AsyncMock()

    @pytest.fixture
    def mock_session_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_jwt_signer(self):
        return Mock()

    @pytest.fixture
    def login_use_case(self, mock_cognito_client, mock_session_repo, mock_jwt_signer):
        return LoginUserUseCase(
            cognito_client=mock_cognito_client,
            session_repository=mock_session_repo,
            jwt_signer=mock_jwt_signer,
            # ... other dependencies
        )

    @pytest.mark.asyncio
    async def test_login_success_with_cipher(
        self, login_use_case, mock_cognito_client, mock_session_repo
    ):
        # Arrange
        username = "test@example.com"
        cipher_envelope = Mock()
        mock_cognito_client.authenticate_user.return_value = Mock(
            user_sub="cognito-sub-123",
            access_token="cognito-access-token",
            refresh_token="cognito-refresh-token"
        )

        # Act
        result = await login_use_case.execute(
            username=username,
            cipher_envelope=cipher_envelope
        )

        # Assert
        assert result.access_token is not None
        assert result.user.email == username
        mock_session_repo.store_session.assert_called_once()
```

**Current Test Files:**
- **Auth Service**: 14 test files covering all use cases and adapters
- **BFF Service**: 5 test files covering HTTP adapters and use cases
- **Events Service**: 3 test files covering Kafka producer and use cases
- **UserProfiles Service**: Tests covering SQL functions and repositories
- **UserSettings Service**: Tests covering DynamoDB operations and OCC

### 11.2 Integration Tests

**Database Integration Tests:**
```python
# apps/userprofiles-service/tests/integration/test_pg_integration.py
import pytest
import asyncpg
from infrastructure.adapters.pg_user_repository import PgUserRepository

@pytest.fixture
async def db_connection():
    conn = await asyncpg.connect("postgresql://postgres:password@localhost:5432/test_db")
    yield conn
    await conn.close()

@pytest.mark.asyncio
async def test_user_crud_integration(db_connection):
    repo = PgUserRepository(connection=db_connection)

    # Create user
    user = await repo.create(
        cognito_sub="test-sub",
        email="test@example.com",
        display_name="Test User"
    )
    assert user.id is not None

    # Get user
    found_user = await repo.find_by_sub("test-sub")
    assert found_user.email == "test@example.com"

    # Update user
    updated_user = await repo.update(user.id, display_name="Updated Name")
    assert updated_user.display_name == "Updated Name"
```

### 11.3 API Tests

**FastAPI Test Client:**
```python
# apps/bff/tests/integration/test_user_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from presentation.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.fixture
def mock_jwt_token():
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

def test_get_user_success(client, mock_jwt_token):
    with patch('presentation.middleware.auth_jwt.verify_jwt') as mock_verify:
        mock_verify.return_value = {"sub": "user-123", "scope": "user.read"}

        response = client.get(
            "/api/v1/user",
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
```

## 12. Environment Configuration

### 12.1 Development Environment Variables

**Required Environment Variables:**
```bash
# Core settings
ENV=development
DEBUG=true

# Database connections
PG_DSN=postgresql://postgres:password@localhost:5432/appdb
REDIS_URL=redis://localhost:6379/0
DYNAMODB_ENDPOINT_URL=http://localhost:4566
DYNAMODB_TABLE_USER_SETTINGS=user_settings_dev

# Kafka
KAFKA_BROKERS=localhost:9092

# AWS Services (development)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test

# Cognito
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=your_cognito_client_id
COGNITO_CLIENT_SECRET=your_cognito_client_secret

# OAuth (optional)
GOOGLE_OAUTH_CLIENT_ID=your_google_client_id
FACEBOOK_OAUTH_CLIENT_ID=your_facebook_client_id

# Service URLs
BFF_API_URL=http://localhost:8080
USERPROFILES_URL=http://localhost:8081
USERSETTINGS_URL=http://localhost:8082
AUTH_SERVICE_URL=http://localhost:8083
EVENTS_SERVICE_URL=http://localhost:8084

# JWT/Crypto
JWT_ISSUER=https://auth.example.com
JWT_AUDIENCE=cloud-app
JWT_ACCESS_TOKEN_TTL_SECONDS=900
JWT_SESSION_TTL_SECONDS=1800

# Service tokens
SVC_TOKEN_TTL_SECONDS=300
SVC_CLIENT_ID_bff=bff-client-id
SVC_CLIENT_SECRET_bff=bff-client-secret

# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=bpt-service
OTEL_RESOURCE_ATTRIBUTES=service.name=bpt,service.version=1.0.0
```

### 12.2 Production Environment Variables

**Production Overrides:**
```bash
# Core settings
ENV=production
DEBUG=false

# Database connections (RDS/ElastiCache endpoints)
PG_DSN=postgresql://username:password@rds-cluster.amazonaws.com:5432/appdb
REDIS_URL=redis://elasticache-cluster.amazonaws.com:6379/0

# DynamoDB (no endpoint URL for production)
DYNAMODB_TABLE_USER_SETTINGS=user_settings_prod

# Kafka (MSK endpoints)
KAFKA_BROKERS=msk-cluster-1.amazonaws.com:9092,msk-cluster-2.amazonaws.com:9092

# AWS (IRSA for pod-level permissions)
AWS_REGION=us-east-1
# AWS_ACCESS_KEY_ID/SECRET not needed with IRSA

# Service URLs (internal Kubernetes services)
USERPROFILES_URL=http://userprofiles-service.bpt-prod.svc.cluster.local:8081
USERSETTINGS_URL=http://usersettings-service.bpt-prod.svc.cluster.local:8082
AUTH_SERVICE_URL=http://auth-service.bpt-prod.svc.cluster.local:8083

# JWT/Crypto (Secrets Manager)
JWT_PRIVATE_KEY_PEM_SECRET_NAME=bpt/jwt-private-key
JWT_PUBLIC_KEY_JWK_SECRET_NAME=bpt/jwt-public-key

# Service tokens (from Secrets Manager)
SVC_CLIENT_SECRET_bff=arn:aws:secretsmanager:us-east-1:account:secret:bpt/svc-bff

# OpenTelemetry (X-Ray)
OTEL_EXPORTER_OTLP_ENDPOINT=http://opentelemetry-collector.istio-system.svc.cluster.local:4317
AWS_XRAY_DAEMON_ADDRESS=xray-daemon.istio-system.svc.cluster.local:2000
```

## 13. Development Workflows

### 13.1 Makefile Commands

```makefile
# Makefile
.PHONY: up down build install fmt lint test precommit

# Development environment
up:
	docker compose -f docker-compose.dev.yml up -d

down:
	docker compose -f docker-compose.dev.yml down -v

build:
	docker compose -f docker-compose.dev.yml build

logs:
	docker compose -f docker-compose.dev.yml logs -f

# Development setup
install:
	pipx run pre-commit install
	cd frontend/web && npm install

# Code quality
fmt:
	ruff format .
	isort .
	cd frontend/web && npm run lint:fix

lint:
	ruff check .
	import-linter lint
	cd frontend/web && npm run lint

# Testing
test:
	pytest -q --tb=short
	cd frontend/web && npm test

test-coverage:
	pytest --cov=apps --cov-report=html --cov-report=term-missing

# Pre-commit
precommit:
	pre-commit run --all-files

# Database migrations
migrate-userprofiles:
	cd apps/userprofiles-service && python scripts/run_pg_migrations.py

migrate-usersettings:
	cd apps/usersettings-service && python scripts/run_dynamodb_migrations.py

# Service management
restart-service:
	docker compose -f docker-compose.dev.yml restart $(SERVICE)

shell-service:
	docker compose -f docker-compose.dev.yml exec $(SERVICE) /bin/bash
```

### 13.2 Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.6.9
  hooks:
  - id: ruff
    args: [--fix, --exit-non-zero-on-fix]
  - id: ruff-format

- repo: https://github.com/pycqa/isort
  rev: 5.13.2
  hooks:
  - id: isort

- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.10.0
  hooks:
  - id: mypy
    additional_dependencies: [types-requests, types-redis]

- repo: https://github.com/seddonym/import-linter
  rev: v2.0
  hooks:
  - id: import-linter

- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v4.6.0
  hooks:
  - id: trailing-whitespace
  - id: end-of-file-fixer
  - id: check-yaml
  - id: check-added-large-files
```

### 13.3 Import Linter Configuration

```ini
# .importlinter
[importlinter]
root_package = apps

[contract:auth_service_layers]
type = layers
name = Auth Service layers
layers =
    apps.auth-service.presentation
    apps.auth-service.application
    apps.auth-service.domain
containers =
    apps.auth-service.infrastructure
ignore_imports =
    apps.auth-service.presentation -> apps.auth-service.infrastructure

[contract:bff_layers]
type = layers
name = BFF layers
layers =
    apps.bff.presentation
    apps.bff.application
    apps.bff.domain
containers =
    apps.bff.infrastructure
ignore_imports =
    apps.bff.presentation -> apps.bff.infrastructure

[contract:events_service_layers]
type = layers
name = Events Service layers
layers =
    apps.events-service.presentation
    apps.events-service.application
    apps.events-service.domain
containers =
    apps.events-service.infrastructure
ignore_imports =
    apps.events-service.presentation -> apps.events-service.infrastructure

[contract:userprofiles_service_layers]
type = layers
name = UserProfiles Service layers
layers =
    apps.userprofiles-service.presentation
    apps.userprofiles-service.application
    apps.userprofiles-service.domain
containers =
    apps.userprofiles-service.infrastructure
ignore_imports =
    apps.userprofiles-service.presentation -> apps.userprofiles-service.infrastructure

[contract:usersettings_service_layers]
type = layers
name = UserSettings Service layers
layers =
    apps.usersettings-service.presentation
    apps.usersettings-service.application
    apps.usersettings-service.domain
containers =
    apps.usersettings-service.infrastructure
ignore_imports =
    apps.usersettings-service.presentation -> apps.usersettings-service.infrastructure
```

## 14. Monitoring & Observability

### 14.1 Health Checks

**Health Check Implementation:**
```python
# Standard health check endpoints for all services
@router.get("/health", response_model=HealthResponse)
async def health():
    """General health check"""
    return HealthResponse(status="healthy", timestamp=datetime.utcnow())

@router.get("/health/ready", response_model=HealthResponse)
async def ready():
    """Readiness probe - check dependencies"""
    # Check database connections, external services
    return HealthResponse(status="ready", timestamp=datetime.utcnow())

@router.get("/health/live", response_model=HealthResponse)
async def live():
    """Liveness probe - basic service health"""
    return HealthResponse(status="alive", timestamp=datetime.utcnow())
```

### 14.2 Structured Logging

**Logging Configuration:**
```python
# shared/python/src/framework/logging/setup.py
import structlog
import logging
import sys

def setup_logging(service_name: str, level: str = "INFO", json_format: bool = True):
    """Configure structured logging"""

    if json_format:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, level.upper())
            ),
            context_class=dict,
            logger_factory=structlog.WriteLoggerFactory(sys.stdout),
            cache_logger_on_first_use=True,
        )

    # Add service context
    structlog.contextvars.bind_contextvars(service=service_name)
```

**Usage in Services:**
```python
# Usage in application code
import structlog

logger = structlog.get_logger(__name__)

# In use cases
logger.info("User login attempt",
           username=username,
           correlation_id=correlation_id,
           trace_id=trace_id)

# In error handling
logger.error("Database connection failed",
            error=str(e),
            database="postgresql",
            operation="user_lookup")
```

### 14.3 OpenTelemetry Integration

**Tracing Configuration:**
```python
# shared/python/src/framework/telemetry/otel.py
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

def init_tracing(service_name: str, otlp_endpoint: str):
    """Initialize OpenTelemetry tracing"""

    # Configure tracer provider
    trace.set_tracer_provider(TracerProvider(
        resource=Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0"
        })
    ))

    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)

    # Auto-instrument frameworks
    FastAPIInstrumentor.instrument()
    HTTPXClientInstrumentor.instrument()
    Psycopg2Instrumentor.instrument()
```

### 14.4 Monitoring Configuration

**OpenTelemetry Collector:**
```yaml
# infrastructure/kubernetes/monitoring/otel-collector.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
  namespace: istio-system
data:
  config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318

    processors:
      batch:

    exporters:
      awsxray:
        region: us-east-1

      prometheusremotewrite:
        endpoint: https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-xxx/api/v1/remote_write
        auth:
          authenticator: sigv4auth

    extensions:
      sigv4auth:
        region: us-east-1

    service:
      extensions: [sigv4auth]
      pipelines:
        traces:
          receivers: [otlp]
          processors: [batch]
          exporters: [awsxray]
        metrics:
          receivers: [otlp]
          processors: [batch]
          exporters: [prometheusremotewrite]

---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: otel-collector
  namespace: istio-system
spec:
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      containers:
      - name: otel-collector
        image: otel/opentelemetry-collector-contrib:latest
        command: ["/otelcol-contrib"]
        args: ["--config=/etc/otel/config.yaml"]
        volumeMounts:
        - name: config
          mountPath: /etc/otel
        ports:
        - containerPort: 4317
        - containerPort: 4318
      volumes:
      - name: config
        configMap:
          name: otel-collector-config
```

**Fluent Bit for Logs:**
```yaml
# infrastructure/kubernetes/monitoring/fluent-bit.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: istio-system
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         1
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf

    [INPUT]
        Name              tail
        Path              /var/log/containers/*bpt*.log
        Parser            cri
        Tag               kube.*
        Refresh_Interval  5
        Mem_Buf_Limit     50MB

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Merge_Log           On

    [OUTPUT]
        Name                cloudwatch_logs
        Match               kube.*
        region              us-east-1
        log_group_name      /aws/eks/bpt/application
        log_stream_prefix   pod-
        auto_create_group   true
```

## 15. Security Implementation

### 15.1 Service Token Validation Middleware

```python
# apps/userprofiles-service/presentation/middleware/auth_svc.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
from framework.auth.jwt_verify import JWTVerifier

class Principal:
    def __init__(self, svc_sub: str, actor_sub: str|None, actor_scope: str|None, roles: list[str]|None):
        self.svc_sub = svc_sub
        self.actor_sub = actor_sub
        self.actor_scope = actor_scope
        self.roles = roles or []

class RequireServiceToken(BaseHTTPMiddleware):
    def __init__(self, app, jwks_client, audience="internal"):
        super().__init__(app)
        self.jwks = jwks_client
        self.audience = audience

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/internal/"):
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")

        token = auth.split(" ", 1)[1]

        try:
            claims = jwt.decode(
                token,
                self.jwks,
                algorithms=["ES256"],
                audience=self.audience,
                options={"require": ["exp", "aud", "sub"]}
            )

            if claims.get("token_use") != "svc":
                raise HTTPException(status_code=403, detail="Invalid token use")

            act = claims.get("act", {}) if isinstance(claims.get("act"), dict) else {}

            request.state.principal = Principal(
                svc_sub=claims["sub"],
                actor_sub=act.get("sub"),
                actor_scope=act.get("scope"),
                roles=act.get("roles") or []
            )

        except jwt.PyJWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

        return await call_next(request)
```

### 15.2 JWKS Implementation

```python
# apps/auth-service/presentation/api/jwks_routes.py
from fastapi import APIRouter, Depends
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
import json

router = APIRouter()

@router.get("/.well-known/jwks.json")
async def get_jwks(signer=Depends(get_jwt_signer)):
    """Return JSON Web Key Set for JWT verification"""

    # Get public key from signer
    public_key = signer.get_public_key()

    # Extract coordinates for ES256
    public_numbers = public_key.public_numbers()
    x = public_numbers.x.to_bytes(32, 'big')
    y = public_numbers.y.to_bytes(32, 'big')

    jwk = {
        "kty": "EC",
        "use": "sig",
        "crv": "P-256",
        "kid": signer.kid,
        "x": base64url_encode(x),
        "y": base64url_encode(y),
        "alg": "ES256"
    }

    return {"keys": [jwk]}
```

### 15.3 Secrets Management

**Environment Variables for Development:**
```bash
# Development - direct values
JWT_PRIVATE_KEY_PEM="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
COGNITO_CLIENT_SECRET="your-cognito-client-secret"
SVC_CLIENT_SECRET_bff="bff-service-secret"
```

**Production - AWS Secrets Manager:**
```python
# shared/python/src/framework/config/secrets.py
import boto3
import json
from botocore.exceptions import ClientError

class SecretsManager:
    def __init__(self, region_name: str = "us-east-1"):
        self.client = boto3.client('secretsmanager', region_name=region_name)

    def get_secret(self, secret_name: str) -> str:
        """Get secret value from AWS Secrets Manager"""
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return response['SecretString']
        except ClientError as e:
            raise Exception(f"Failed to retrieve secret {secret_name}: {e}")

    def get_secret_json(self, secret_name: str) -> dict:
        """Get secret as JSON object"""
        secret_value = self.get_secret(secret_name)
        return json.loads(secret_value)

# Usage in service initialization
secrets = SecretsManager()
jwt_private_key = secrets.get_secret("bpt/jwt-private-key")
cognito_secrets = secrets.get_secret_json("bpt/cognito-credentials")
```

## 16. Data Flow Examples

### 16.1 User Login Flow (Complete)

**1. Frontend Session Cipher Setup:**
```typescript
// 1. Client requests cipher session
const sessionResult = await createSession().unwrap();

// 2. Client encrypts password using WebCrypto
const cipherEnvelope = await encryptPassword({
  serverPublicKeyJwk: sessionResult.server_public_key_jwk,
  sid: sessionResult.sid,
  password: formData.password,
});
```

**2. Backend Authentication:**
```python
# 3. Server decrypts password
cipher_service.decrypt_envelope(
    cipher_envelope.client_public_key_jwk,
    cipher_envelope.nonce,
    cipher_envelope.password_enc,
    cipher_envelope.sid
)

# 4. Authenticate with Cognito
cognito_result = await cognito_client.authenticate_user(username, decrypted_password)

# 5. Create session and JWT
session = await session_repository.create_session(
    user_id=user.id,
    cognito_sub=cognito_result.user_sub,
    refresh_token=cognito_result.refresh_token
)

access_token = jwt_signer.mint(
    sub=user.id,
    sid=session.sid,
    scopes="user.read usersettings.read usersettings.write",
    extra={"roles": ["user"], "idp": "cognito"}
)
```

**3. Frontend Token Storage:**
```typescript
// 6. Store access token in memory only
dispatch(setCredentials({
  accessToken: result.access_token,
  user: result.user
}));

// Session ID stored in httpOnly cookie by server
```

### 16.2 BFF API Call Flow

**1. BFF Receives User Request:**
```python
# BFF validates user JWT and extracts claims
principal = extract_principal_from_jwt(request)  # user-123, scopes: user.read

# BFF gets service token with actor context
service_token = service_token_client.get(
    actor_sub=principal.sub,           # user-123
    actor_scope=principal.scope,       # user.read usersettings.write
    actor_roles=principal.roles        # ["user"]
)
```

**2. BFF Calls Microservice:**
```python
# BFF makes HTTP call with service token
headers = {"Authorization": f"Bearer {service_token}"}
response = await httpx.get(
    f"{userprofiles_url}/internal/users/by-sub/{principal.sub}",
    headers=headers
)
```

**3. Microservice Validates Service Token:**
```python
# Microservice middleware validates service token
claims = jwt.decode(token, jwks, algorithms=["ES256"], audience="internal")

# Extract actor context
principal = Principal(
    svc_sub="spn:bff",                    # Service principal
    actor_sub="user-123",                 # On-behalf-of user
    actor_scope="user.read usersettings.write",
    roles=["user"]
)

# Business logic uses actor context for authorization
user = await get_user_use_case.execute(actor_sub=principal.actor_sub)
```

### 16.3 Event Publishing Flow

**1. Domain Event Creation:**
```python
# In UserProfiles service after user creation
await event_publisher.publish_event(
    event_type=EventType.USER_CREATED,
    payload={
        "email": user.email,
        "display_name": user.display_name,
        "cognito_sub": user.cognito_sub
    },
    user_id=str(user.id),
    correlation_id=request_context.correlation_id,
    trace_id=request_context.trace_id,
    source="userprofiles-service"
)
```

**2. Event Processing:**
```python
# Events service processes and routes to Kafka
event = Event.create(
    event_type="user.created",
    payload=payload,
    user_id=user_id,
    correlation_id=correlation_id,
    trace_id=trace_id,
    source=source
)

# Determine topic from mapping
topic = EVENT_TOPIC_MAPPING.get(EventType.USER_CREATED, TopicName.SYSTEM_EVENTS)

# Store in event store
await event_store.store_event(event)

# Publish to Kafka
await kafka_producer.publish_event(event, topic)
```

**3. Event Consumption (if implemented):**
```python
# Consumer processes events from Kafka topics
async def handle_user_created(event: Event):
    logger.info("Processing user created event",
               event_id=event.event_id,
               user_id=event.user_id)

    # Business logic for user creation
    await send_welcome_email(event.payload["email"])
    await create_default_settings(event.user_id)
```

## 17. Key Implementation Files

### 17.1 Critical Path Files

**Authentication Core:**
- `apps/auth-service/infrastructure/adapters/crypto/ecdh_kms.py` - Session cipher
- `apps/auth-service/infrastructure/adapters/crypto/es256_signer.py` - JWT signing
- `apps/auth-service/application/use_cases/login_user.py` - Login orchestration
- `frontend/web/src/lib/sessionCipher.ts` - Client-side encryption

**Service Communication:**
- `apps/auth-service/application/use_cases/svc_token.py` - Service token issuance
- `shared/python/src/framework/auth/service_tokens.py` - Service token client
- `apps/bff/infrastructure/adapters/http_userprofiles_client.py` - BFF→UserProfiles

**Data Layer:**
- `apps/userprofiles-service/db/functions/users.sql` - PostgreSQL functions
- `apps/usersettings-service/infrastructure/adapters/ddb_settings_repository.py` - DynamoDB with OCC
- `apps/userprofiles-service/scripts/run_pg_migrations.py` - PostgreSQL migrations

**Event System:**
- `apps/events-service/infrastructure/adapters/kafka/kafka_producer.py` - Kafka producer
- `apps/events-service/application/use_cases/publish_event.py` - Event publishing
- `apps/events-service/application/use_cases/replay_events.py` - Event replay

**Frontend Integration:**
- `frontend/web/src/store/api.ts` - RTK Query API definitions
- `frontend/web/src/components/AuthForm.tsx` - Authentication UI with OAuth
- `frontend/web/src/store/authSlice.ts` - Authentication state

### 17.2 Configuration Files

**Development Environment:**
- `docker-compose.dev.yml` - Complete development stack
- `.env.example` - Environment variable template
- `Makefile` - Development workflows

**Production Deployment:**
- `infrastructure/kubernetes/helm-charts/cloud-app/` - Kubernetes deployment
- `infrastructure/kubernetes/istio/` - Service mesh configuration
- `infrastructure/terraform/` - AWS infrastructure

**Code Quality:**
- `.pre-commit-config.yaml` - Code quality automation
- `.importlinter` - Architecture boundary enforcement
- `pyproject.toml` (per service) - Python dependencies and tools

## 18. Future Implementation Roadmap

### 18.1 Immediate Next Steps

**Infrastructure Completion:**
1. **Complete Terraform modules** for production AWS resources
2. **Finalize Kubernetes manifests** with proper resource limits and security contexts
3. **Implement CI/CD pipelines** with GitOps deployment
4. **Add comprehensive monitoring** with Prometheus metrics and Grafana dashboards

**Event System Enhancement:**
1. **Implement event consumers** for business logic processing
2. **Add event schema validation** with versioning support
3. **Implement event sourcing** for audit trails
4. **Add event replay UI** for operations teams

### 18.2 Advanced Features

**Security Enhancements:**
1. **API rate limiting** and DDoS protection
2. **Advanced audit logging** with tamper detection
3. **Zero-trust networking** with Istio authorization policies
4. **Secrets rotation** automation

**Operational Excellence:**
1. **SLI/SLO definitions** with alerting
2. **Chaos engineering** testing
3. **Performance optimization** based on production metrics
4. **Cost optimization** with resource right-sizing

**Business Features:**
1. **Multi-tenancy support** with data isolation
2. **Feature flags** for gradual rollouts
3. **Advanced user analytics** and insights
4. **Integration APIs** for third-party services

---

## Conclusion

This system design document captures the complete implementation state of the BPT platform. Every component, API endpoint, database schema, and configuration file described here reflects the actual working codebase with 136 Python files across 5 microservices, comprehensive unit tests, and a fully functional React frontend.

The architecture successfully implements:
- ✅ **Clean Architecture** with proper layer separation
- ✅ **Session cipher security** for password protection
- ✅ **OAuth2 integration** with Google/Facebook
- ✅ **Service token authentication** with actor claims
- ✅ **Event-driven architecture** with Kafka and DLQ
- ✅ **Modern frontend** with React 18 and RTK Query
- ✅ **Comprehensive testing** strategy
- ✅ **Infrastructure as Code** foundations

This document serves as the authoritative source for understanding, maintaining, and extending the BPT platform. Every detail provided can be used to recreate the exact same implementation with Claude Code or similar AI coding assistants.