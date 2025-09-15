#!/bin/bash

echo "Setting up Cognito User Pool in LocalStack..."

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to be ready..."
sleep 10

# Check if awslocal is available
if ! command -v awslocal &> /dev/null; then
    echo "awslocal not found, trying aws with endpoint-url"
    AWS_CMD="aws --endpoint-url=http://localhost:4566"
else
    AWS_CMD="awslocal"
fi

# Create Cognito User Pool
echo "Creating User Pool..."
USER_POOL_RESPONSE=$($AWS_CMD cognito-idp create-user-pool \
    --pool-name "dev-user-pool" \
    --auto-verified-attributes email \
    --username-attributes email \
    --region us-east-1)

# Extract User Pool ID (simple grep approach since jq is not available)
USER_POOL_ID=$(echo "$USER_POOL_RESPONSE" | grep -oP '"Id":\s*"\K[^"]+' | head -1)
echo "Created User Pool with ID: $USER_POOL_ID"

if [ -z "$USER_POOL_ID" ]; then
    echo "Failed to create User Pool. Full response:"
    echo "$USER_POOL_RESPONSE"
    exit 1
fi

# Create Cognito User Pool Client
echo "Creating User Pool Client..."
CLIENT_RESPONSE=$($AWS_CMD cognito-idp create-user-pool-client \
    --user-pool-id "$USER_POOL_ID" \
    --client-name "dev-client" \
    --generate-secret \
    --explicit-auth-flows ADMIN_NO_SRP_AUTH ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
    --region us-east-1)

# Extract Client ID and Secret
CLIENT_ID=$(echo "$CLIENT_RESPONSE" | grep -oP '"ClientId":\s*"\K[^"]+')
CLIENT_SECRET=$(echo "$CLIENT_RESPONSE" | grep -oP '"ClientSecret":\s*"\K[^"]+')

echo "Created User Pool Client with ID: $CLIENT_ID"
echo "Client Secret: ${CLIENT_SECRET:0:10}***"

# Store the configuration in a file for reference
cat > /tmp/cognito-config.env << EOF
COGNITO_USER_POOL_ID=$USER_POOL_ID
COGNITO_CLIENT_ID=$CLIENT_ID
COGNITO_CLIENT_SECRET=$CLIENT_SECRET
AWS_ENDPOINT_URL=http://localhost:4566
EOF

echo "Cognito configuration saved to /tmp/cognito-config.env"
echo "USER_POOL_ID: $USER_POOL_ID"
echo "CLIENT_ID: $CLIENT_ID"
echo "CLIENT_SECRET: $CLIENT_SECRET"
echo "Cognito setup complete!"