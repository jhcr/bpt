-- Initialize database with extensions, schema, and roles
-- This is run first during database initialization

-- Create required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

-- Create application schema
CREATE SCHEMA IF NOT EXISTS userprofiles AUTHORIZATION CURRENT_USER;

-- Create migration tracking table
CREATE TABLE IF NOT EXISTS userprofiles.schema_migrations (
    filename TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);