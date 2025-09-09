-- Add phone number field to users table
ALTER TABLE userprofiles.users 
ADD COLUMN IF NOT EXISTS phone TEXT;