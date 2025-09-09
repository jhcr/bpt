-- Maintenance procedures for user profiles

-- Rebuild all indexes on users table
CREATE OR REPLACE PROCEDURE userprofiles.rebuild_user_indexes()
LANGUAGE plpgsql AS $$
BEGIN
    -- Rebuild indexes concurrently to minimize downtime
    REINDEX INDEX CONCURRENTLY userprofiles.idx_users_email;
    REINDEX INDEX CONCURRENTLY userprofiles.idx_users_cognito_sub;
    REINDEX INDEX CONCURRENTLY userprofiles.idx_users_active;
    REINDEX INDEX CONCURRENTLY userprofiles.idx_users_created_at;
    
    RAISE NOTICE 'User indexes rebuilt successfully';
END;
$$;

-- Update statistics for better query planning
CREATE OR REPLACE PROCEDURE userprofiles.update_user_statistics()
LANGUAGE plpgsql AS $$
BEGIN
    ANALYZE userprofiles.users;
    RAISE NOTICE 'User table statistics updated';
END;
$$;

-- Clean up old records (if needed for GDPR compliance)
CREATE OR REPLACE PROCEDURE userprofiles.cleanup_inactive_users(
    p_days_inactive INTEGER DEFAULT 365
)
LANGUAGE plpgsql AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- This is a placeholder for GDPR compliance
    -- In practice, you might want to anonymize rather than delete
    
    DELETE FROM userprofiles.users 
    WHERE is_active = FALSE 
    AND updated_at < (NOW() - INTERVAL '1 day' * p_days_inactive);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RAISE NOTICE 'Cleaned up % inactive users older than % days', deleted_count, p_days_inactive;
END;
$$;