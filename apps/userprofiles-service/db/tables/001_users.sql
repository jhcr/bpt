-- User profiles table
CREATE TABLE IF NOT EXISTS userprofiles.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_sub TEXT UNIQUE NOT NULL,
    email CITEXT UNIQUE NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON userprofiles.users(email);
CREATE INDEX IF NOT EXISTS idx_users_cognito_sub ON userprofiles.users(cognito_sub);
CREATE INDEX IF NOT EXISTS idx_users_active ON userprofiles.users(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_users_created_at ON userprofiles.users(created_at);

-- Trigger to automatically update updated_at
CREATE OR REPLACE FUNCTION userprofiles.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_users_updated_at ON userprofiles.users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON userprofiles.users
    FOR EACH ROW
    EXECUTE FUNCTION userprofiles.update_updated_at_column();