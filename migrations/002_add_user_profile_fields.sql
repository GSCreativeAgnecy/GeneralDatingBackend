-- Migration: Add new user profile fields
BEGIN;

ALTER TABLE users RENAME COLUMN name TO first_name;
ALTER TABLE users ADD COLUMN last_name VARCHAR(64) DEFAULT '';

ALTER TABLE users ADD COLUMN mother_tongue VARCHAR(32) DEFAULT '';
ALTER TABLE users ADD COLUMN diet VARCHAR(16) DEFAULT '';
ALTER TABLE users ADD COLUMN drinking VARCHAR(16) DEFAULT '';
ALTER TABLE users ADD COLUMN smoking VARCHAR(16) DEFAULT '';
ALTER TABLE users ADD COLUMN sub_caste VARCHAR(64) DEFAULT '';
ALTER TABLE users ADD COLUMN annual_income VARCHAR(64) DEFAULT '';
ALTER TABLE users ADD COLUMN profile_created_by VARCHAR(32) DEFAULT '';
ALTER TABLE users ADD COLUMN contact_visibility VARCHAR(32) DEFAULT '';
ALTER TABLE users ADD COLUMN body_type VARCHAR(32) DEFAULT '';
ALTER TABLE users ADD COLUMN complexion VARCHAR(16) DEFAULT '';
ALTER TABLE users ADD COLUMN physical_status VARCHAR(32) DEFAULT '';

ALTER TABLE users ADD COLUMN horoscope_match BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN nakshatra VARCHAR(32) DEFAULT '';
ALTER TABLE users ADD COLUMN rashi VARCHAR(32) DEFAULT '';
ALTER TABLE users ADD COLUMN gothram VARCHAR(64) DEFAULT '';
ALTER TABLE users ADD COLUMN dosham VARCHAR(16) DEFAULT '';
ALTER TABLE users ADD COLUMN time_of_birth VARCHAR(5) DEFAULT '';
ALTER TABLE users ADD COLUMN place_of_birth VARCHAR(64) DEFAULT '';
ALTER TABLE users ADD COLUMN horoscope_compatibility_score INTEGER DEFAULT NULL;

ALTER TABLE users ADD COLUMN family_type VARCHAR(32) DEFAULT '';
ALTER TABLE users ADD COLUMN family_values VARCHAR(32) DEFAULT '';
ALTER TABLE users ADD COLUMN about_family TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN father_occupation VARCHAR(128) DEFAULT '';
ALTER TABLE users ADD COLUMN mother_occupation VARCHAR(128) DEFAULT '';
ALTER TABLE users ADD COLUMN brothers INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN sisters INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN family_location VARCHAR(64) DEFAULT '';

ALTER TABLE users ADD COLUMN match_request_mode BOOLEAN DEFAULT FALSE;

ALTER TABLE user_preferences ADD COLUMN preferred_height_min INTEGER DEFAULT NULL;
ALTER TABLE user_preferences ADD COLUMN preferred_height_max INTEGER DEFAULT NULL;
ALTER TABLE user_preferences ADD COLUMN preferred_marital_status TEXT DEFAULT '';
ALTER TABLE user_preferences ADD COLUMN preferred_mother_tongue TEXT DEFAULT '';
ALTER TABLE user_preferences ADD COLUMN preferred_caste TEXT DEFAULT '';
ALTER TABLE user_preferences ADD COLUMN preferred_diet VARCHAR(16) DEFAULT '';
ALTER TABLE user_preferences ADD COLUMN preferred_country TEXT DEFAULT '';
ALTER TABLE user_preferences ADD COLUMN preferred_state TEXT DEFAULT '';
ALTER TABLE user_preferences ADD COLUMN preferred_employed_in TEXT DEFAULT '';
ALTER TABLE user_preferences ADD COLUMN preferred_education VARCHAR(128) DEFAULT '';
ALTER TABLE user_preferences ADD COLUMN preferred_physical_status VARCHAR(32) DEFAULT '';
ALTER TABLE user_preferences ADD COLUMN preferred_family_values VARCHAR(32) DEFAULT '';

COMMIT;
