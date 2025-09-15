-- User CRUD functions that return rows or boolean
-- These functions provide a clean interface for user operations

-- Create user (returns full row)
DROP FUNCTION IF EXISTS userprofiles.create_user;
CREATE FUNCTION userprofiles.create_user(
    p_id UUID,
    p_cognito_sub TEXT,
    p_email CITEXT,
    p_display_name TEXT,
    p_avatar_url TEXT,
    p_phone TEXT
) RETURNS TABLE(id uuid,
    cognito_sub text,
    email citext,
    display_name text,
    avatar_url text,
	phone text,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp)
LANGUAGE sql AS $$
    INSERT INTO userprofiles.users (
        id, cognito_sub, email, display_name, avatar_url, phone,
        is_active, created_at, updated_at
    )
    VALUES (
        COALESCE(p_id, gen_random_uuid()),
        p_cognito_sub,
        p_email,
        p_display_name,
        p_avatar_url,
        p_phone,
        TRUE,
        NOW(),
        NOW()
    )
    RETURNING id, cognito_sub, email, display_name, avatar_url, phone,
        is_active, created_at, updated_at;
$$;

-- Get user by ID (single-statement SQL function)
DROP FUNCTION IF EXISTS userprofiles.get_user_by_id;
CREATE FUNCTION userprofiles.get_user_by_id(p_id UUID)
RETURNS TABLE(id uuid,
    cognito_sub text,
    email citext,
    display_name text,
    avatar_url text,
	phone text,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp)
LANGUAGE sql AS $$
    SELECT 
        id, cognito_sub, email, display_name, avatar_url, phone,
        is_active, created_at, updated_at
    FROM userprofiles.users
    WHERE id = p_id;
$$;

-- Get user by cognito_sub
DROP FUNCTION IF EXISTS userprofiles.get_user_by_sub;
CREATE FUNCTION userprofiles.get_user_by_sub(p_cognito_sub TEXT)
RETURNS TABLE(id uuid,
    cognito_sub text,
    email citext,
    display_name text,
    avatar_url text,
	phone text,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp)
LANGUAGE sql AS $$
    SELECT 
        id, cognito_sub, email, display_name, avatar_url, phone,
        is_active, created_at, updated_at
    FROM userprofiles.users
    WHERE cognito_sub = p_cognito_sub;
$$;

-- Get user by email
DROP FUNCTION IF EXISTS userprofiles.get_user_by_email;
CREATE FUNCTION userprofiles.get_user_by_email(p_email CITEXT)
RETURNS TABLE(id uuid,
    cognito_sub text,
    email citext,
    display_name text,
    avatar_url text,
	phone text,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp)
LANGUAGE sql AS $$
    SELECT
        id, cognito_sub, email, display_name, avatar_url, phone,
        is_active, created_at, updated_at
    FROM userprofiles.users
    WHERE email = p_email;
$$;

-- Update user (returns full row)
DROP FUNCTION IF EXISTS userprofiles.update_user;
CREATE FUNCTION userprofiles.update_user(
    p_id UUID,
    p_email CITEXT DEFAULT NULL,
    p_display_name TEXT DEFAULT NULL,
    p_avatar_url TEXT DEFAULT NULL,
    p_phone TEXT DEFAULT NULL,
    p_is_active BOOLEAN DEFAULT NULL
)
RETURNS TABLE(id uuid,
    cognito_sub text,
    email citext,
    display_name text,
    avatar_url text,
	phone text,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp)
LANGUAGE sql AS $$
    UPDATE userprofiles.users
    SET
        email = COALESCE(p_email, email),
        display_name = COALESCE(p_display_name, display_name),
        avatar_url = COALESCE(p_avatar_url, avatar_url),
        phone = COALESCE(p_phone, phone),
        is_active = COALESCE(p_is_active, is_active),
        updated_at = NOW()
    WHERE id = p_id
    RETURNING id, cognito_sub, email, display_name, avatar_url, phone,
    is_active, created_at, updated_at;
$$;

-- Delete user (returns deleted row)
DROP FUNCTION IF EXISTS userprofiles.delete_user;
CREATE FUNCTION userprofiles.delete_user(p_id UUID)
RETURNS TABLE(id uuid,
    cognito_sub text,
    email citext,
    display_name text,
    avatar_url text,
	phone text,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp)
LANGUAGE sql AS $$
    DELETE FROM userprofiles.users
    WHERE id = p_id
    RETURNING id, cognito_sub, email, display_name, avatar_url, phone,
        is_active, created_at, updated_at;
$$;

-- Soft delete user (returns updated row)
DROP FUNCTION IF EXISTS userprofiles.soft_delete_user;
CREATE FUNCTION userprofiles.soft_delete_user(p_id UUID)
RETURNS TABLE(id uuid,
    cognito_sub text,
    email citext,
    display_name text,
    avatar_url text,
	phone text,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp)
LANGUAGE sql AS $$
    UPDATE userprofiles.users
    SET is_active = FALSE, updated_at = NOW()
    WHERE id = p_id AND is_active = TRUE
    RETURNING id, cognito_sub, email, display_name, avatar_url, phone,
        is_active, created_at, updated_at;
$$;

-- List active users with pagination
DROP FUNCTION IF EXISTS userprofiles.list_active_users;
CREATE FUNCTION userprofiles.list_active_users(p_limit INTEGER DEFAULT 100, p_offset INTEGER DEFAULT 0)
RETURNS TABLE(id uuid,
    cognito_sub text,
    email citext,
    display_name text,
    avatar_url text,
	phone text,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp)
LANGUAGE sql AS $$
    SELECT 
        id, cognito_sub, email, display_name, avatar_url, phone,
        is_active, created_at, updated_at
    FROM userprofiles.users
    WHERE is_active = true
    ORDER BY created_at DESC
    LIMIT p_limit OFFSET p_offset;
$$;

-- Count active users
DROP FUNCTION IF EXISTS userprofiles.count_active_users;
CREATE FUNCTION userprofiles.count_active_users()
RETURNS INTEGER
LANGUAGE sql AS $$
    SELECT COUNT(*)::INTEGER FROM userprofiles.users WHERE is_active = true;
$$;