# Cloud-Native App - Istio@EKS

**Cloud-Native App — Istio@EKS · API Gateway · Sidecar-First · Clean Architecture · Custom Auth UI · First-Party JWT · Service Tokens**

This is a production-ready cloud-native application built with:
- **Web:** React + Vite SPA with custom auth UI
- **Mobile:** React Native (Expo)
- **Backend:** Python 3.12 + FastAPI microservices
- **Infrastructure:** EKS + Istio service mesh
- **Security:** First-party JWT + service tokens + mTLS

## Architecture

- **BFF** - Backend for Frontend (API composition, no DB)
- **Auth Service** - Cognito broker, JWT issuer, session management
- **UserProfiles Service** - User data (PostgreSQL + SQL functions)
- **UserSettings Service** - User preferences (DynamoDB + migrations)
- **Events Service** - Event streaming (Kafka/MSK)

## Quick Start

```bash
# Install dependencies
make install

# Start local development
make up

# Run tests
make test

# Format and lint
make fmt
make lint
```

## Development

See `docs/` for detailed documentation and runbooks.

## Infrastructure

- EKS cluster with Istio service mesh
- API Gateway + NLB ingress
- Aurora PostgreSQL, DynamoDB, ElastiCache Redis
- MSK (Kafka), Cognito
- Observability: X-Ray, CloudWatch, AMP/AMG