#!/bin/bash
# Smoke tests for all services

set -e

BFF_URL=${BFF_URL:-http://localhost:8080}
AUTH_URL=${AUTH_URL:-http://localhost:8083}
USERPROFILES_URL=${USERPROFILES_URL:-http://localhost:8081}
USERSETTINGS_URL=${USERSETTINGS_URL:-http://localhost:8082}

echo "🧪 Running smoke tests..."
echo "========================"

# Health checks
echo "🏥 Health checks..."
curl -f $BFF_URL/health || echo "❌ BFF health check failed"
curl -f $AUTH_URL/health || echo "❌ Auth service health check failed"
curl -f $USERPROFILES_URL/health || echo "❌ UserProfiles health check failed"
curl -f $USERSETTINGS_URL/health || echo "❌ UserSettings health check failed"

# Auth service endpoints
echo "🔐 Auth service tests..."
curl -f $AUTH_URL/auth/.well-known/jwks.json || echo "❌ JWKS endpoint failed"
curl -f $AUTH_URL/auth/session -X POST -H "Content-Type: application/json" -d '{}' || echo "❌ Session endpoint failed"

# BFF endpoints (should require auth)
echo "🌐 BFF tests..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $BFF_URL/api/v1/user)
if [ "$HTTP_CODE" == "401" ]; then
    echo "✅ BFF auth protection working"
else
    echo "❌ BFF auth protection not working (got $HTTP_CODE)"
fi

echo "✅ Smoke tests completed!"