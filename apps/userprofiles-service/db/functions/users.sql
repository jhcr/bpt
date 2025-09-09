-- User CRUD functions that return rows or boolean
-- These functions provide a clean interface for user operations

-- Create user function (returns row)
CREATE OR REPLACE FUNCTION userprofiles.create_user(
    p_id UUID,
    p_cognito_sub TEXT, 
    p_email CITEXT, 
    p_display_name TEXT, 
    p_avatar_url TEXT
) RETURNS userprofiles.users
LANGUAGE plpgsql AS $$
DECLARE 
    r userprofiles.users%ROWTYPE;
BEGIN
    INSERT INTO userprofiles.users (id, cognito_sub, email, display_name, avatar_url)
    VALUES (COALESCE(p_id, gen_random_uuid()), p_cognito_sub, p_email, p_display_name, p_avatar_url)
    RETURNING * INTO r;
    
    RETURN r;
END;
$$;

-- Get user by ID (returns row)
CREATE OR REPLACE FUNCTION userprofiles.get_user_by_id(p_id UUID)
RETURNS userprofiles.users
LANGUAGE plpgsql AS $$
DECLARE 
    r userprofiles.users%ROWTYPE;
BEGIN 
    SELECT * INTO r FROM userprofiles.users WHERE id = p_id;
    RETURN r; 
END;
$$;

-- Find user by cognito_sub (returns row)
CREATE OR REPLACE FUNCTION userprofiles.find_user_by_sub(p_cognito_sub TEXT)
RETURNS userprofiles.users
LANGUAGE plpgsql AS $$
DECLARE 
    r userprofiles.users%ROWTYPE;
BEGIN 
    SELECT * INTO r FROM userprofiles.users WHERE cognito_sub = p_cognito_sub;
    RETURN r; 
END;
$$;

-- Find user by email (returns row)
CREATE OR REPLACE FUNCTION userprofiles.find_user_by_email(p_email CITEXT)
RETURNS userprofiles.users
LANGUAGE plpgsql AS $$
DECLARE 
    r userprofiles.users%ROWTYPE;
BEGIN 
    SELECT * INTO r FROM userprofiles.users WHERE email = p_email;
    RETURN r; 
END;
$$;

-- Update user (returns row)
CREATE OR REPLACE FUNCTION userprofiles.update_user(
    p_id UUID,
    p_email CITEXT DEFAULT NULL,
    p_display_name TEXT DEFAULT NULL,
    p_avatar_url TEXT DEFAULT NULL,
    p_is_active BOOLEAN DEFAULT NULL,
    p_phone TEXT DEFAULT NULL
) RETURNS userprofiles.users
LANGUAGE plpgsql AS $$
DECLARE 
    r userprofiles.users%ROWTYPE;
BEGIN
    UPDATE userprofiles.users
    SET email = COALESCE(p_email, email),
        display_name = COALESCE(p_display_name, display_name),
        avatar_url = COALESCE(p_avatar_url, avatar_url),
        is_active = COALESCE(p_is_active, is_active),
        phone = COALESCE(p_phone, phone),
        updated_at = NOW()
    WHERE id = p_id
    RETURNING * INTO r;
    
    RETURN r;
END;
$$;

-- Delete user (returns boolean)
CREATE OR REPLACE FUNCTION userprofiles.delete_user(p_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql AS $$
DECLARE 
    deleted BOOLEAN := FALSE;
BEGIN 
    DELETE FROM userprofiles.users WHERE id = p_id;
    GET DIAGNOSTICS deleted = FOUND;
    RETURN deleted; 
END;
$$;

-- Soft delete user (returns boolean)
CREATE OR REPLACE FUNCTION userprofiles.soft_delete_user(p_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql AS $$
DECLARE 
    updated BOOLEAN := FALSE;
BEGIN 
    UPDATE userprofiles.users 
    SET is_active = FALSE, updated_at = NOW()
    WHERE id = p_id AND is_active = TRUE;
    GET DIAGNOSTICS updated = FOUND;
    RETURN updated; 
END;
$$;

-- Get active users count
CREATE OR REPLACE FUNCTION userprofiles.get_active_users_count()
RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE 
    user_count INTEGER;
BEGIN 
    SELECT COUNT(*) INTO user_count 
    FROM userprofiles.users 
    WHERE is_active = TRUE;
    RETURN user_count; 
END;
$$;

-- Search users by email pattern (returns table)
CREATE OR REPLACE FUNCTION userprofiles.search_users_by_email(
    p_email_pattern TEXT,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS SETOF userprofiles.users
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM userprofiles.users 
    WHERE email ILIKE p_email_pattern 
    AND is_active = TRUE
    ORDER BY created_at DESC
    LIMIT p_limit OFFSET p_offset;
END;
$$;