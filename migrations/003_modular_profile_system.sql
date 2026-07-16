-- Migration: Modular profile system v2 — Enhanced (lookup tables, versioning, moderation, search)
-- Run with: psql -d ardhang -f 003_modular_profile_system.sql

BEGIN;

-- 1. Lookup tables for standardised dropdown values
CREATE TABLE IF NOT EXISTS lookup_religions (
    id              SERIAL PRIMARY KEY,
    value           VARCHAR(64)  NOT NULL UNIQUE,
    label           VARCHAR(128) NOT NULL,
    label_hi        VARCHAR(128),
    display_order   INTEGER      NOT NULL DEFAULT 0,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS lookup_castes (
    id              SERIAL PRIMARY KEY,
    value           VARCHAR(64)  NOT NULL UNIQUE,
    label           VARCHAR(128) NOT NULL,
    label_hi        VARCHAR(128),
    display_order   INTEGER      NOT NULL DEFAULT 0,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS lookup_occupations (
    id              SERIAL PRIMARY KEY,
    value           VARCHAR(64)  NOT NULL UNIQUE,
    label           VARCHAR(128) NOT NULL,
    label_hi        VARCHAR(128),
    category        VARCHAR(64),
    display_order   INTEGER      NOT NULL DEFAULT 0,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS lookup_educations (
    id              SERIAL PRIMARY KEY,
    value           VARCHAR(64)  NOT NULL UNIQUE,
    label           VARCHAR(128) NOT NULL,
    label_hi        VARCHAR(128),
    display_order   INTEGER      NOT NULL DEFAULT 0,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS lookup_languages (
    id              SERIAL PRIMARY KEY,
    value           VARCHAR(64)  NOT NULL UNIQUE,
    label           VARCHAR(128) NOT NULL,
    label_hi        VARCHAR(128),
    display_order   INTEGER      NOT NULL DEFAULT 0,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_lookup_languages_active ON lookup_languages(is_active);

-- Seed lookup data
INSERT INTO lookup_religions (value, label, display_order) VALUES
    ('hindu',     'Hindu',     1),
    ('muslim',    'Muslim',    2),
    ('christian', 'Christian', 3),
    ('sikh',      'Sikh',      4),
    ('jain',      'Jain',      5),
    ('buddhist',  'Buddhist',  6),
    ('parsi',     'Parsi',     7),
    ('jewish',    'Jewish',    8),
    ('other',     'Other',     9)
ON CONFLICT (value) DO NOTHING;

INSERT INTO lookup_occupations (value, label, category, display_order) VALUES
    ('software_engineer',  'Software Engineer',  'Technology',    1),
    ('doctor',             'Doctor',             'Healthcare',    2),
    ('teacher',            'Teacher',            'Education',     3),
    ('business_owner',     'Business Owner',     'Business',      4),
    ('manager',            'Manager',            'Corporate',     5),
    ('accountant',         'Accountant',         'Finance',       6),
    ('lawyer',             'Lawyer',             'Legal',         7),
    ('civil_engineer',     'Civil Engineer',     'Engineering',   8),
    ('government',         'Government Service', 'Government',    9),
    ('student',            'Student',            'Education',    10),
    ('other',              'Other',              'General',      99)
ON CONFLICT (value) DO NOTHING;

INSERT INTO lookup_educations (value, label, display_order) VALUES
    ('high_school',   'High School',        1),
    ('bachelors',     'Bachelors Degree',   2),
    ('masters',       'Masters Degree',     3),
    ('phd',           'Ph.D / Doctorate',   4),
    ('diploma',       'Diploma',            5),
    ('professional',  'Professional Degree', 6),
    ('other',         'Other',             99)
ON CONFLICT (value) DO NOTHING;

INSERT INTO lookup_languages (value, label, display_order) VALUES
    ('hindi',     'Hindi',      1),
    ('telugu',    'Telugu',     2),
    ('tamil',     'Tamil',      3),
    ('marathi',   'Marathi',    4),
    ('gujarati',  'Gujarati',   5),
    ('bengali',   'Bengali',    6),
    ('kannada',   'Kannada',    7),
    ('malayalam', 'Malayalam',  8),
    ('punjabi',   'Punjabi',    9),
    ('odia',      'Odia',      10),
    ('urdu',      'Urdu',      11),
    ('english',   'English',   12),
    ('other',     'Other',     99)
ON CONFLICT (value) DO NOTHING;

-- 2. Profile sections
CREATE TABLE IF NOT EXISTS profile_sections (
    id                  SERIAL PRIMARY KEY,
    key                 VARCHAR(64)  NOT NULL UNIQUE,
    name                VARCHAR(128) NOT NULL,
    name_hi             VARCHAR(128),
    description         TEXT,
    icon                VARCHAR(64),
    display_order       INTEGER      NOT NULL DEFAULT 0,
    completion_weight   DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    visibility_rule     JSONB,
    min_app_version     VARCHAR(16),
    is_active           BOOLEAN      NOT NULL DEFAULT TRUE,
    is_system           BOOLEAN      NOT NULL DEFAULT FALSE,
    created_by          VARCHAR(20),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- 3. Profile field definitions
CREATE TABLE IF NOT EXISTS profile_field_definitions (
    id                  SERIAL PRIMARY KEY,
    section_id          INTEGER      NOT NULL REFERENCES profile_sections(id) ON DELETE CASCADE,
    key                 VARCHAR(64)  NOT NULL UNIQUE,
    label               VARCHAR(128) NOT NULL,
    label_hi            VARCHAR(128),
    field_type          VARCHAR(32)  NOT NULL DEFAULT 'text',
    is_required         BOOLEAN      NOT NULL DEFAULT FALSE,
    is_searchable       BOOLEAN      NOT NULL DEFAULT FALSE,
    is_editable         BOOLEAN      NOT NULL DEFAULT TRUE,
    is_visible          BOOLEAN      NOT NULL DEFAULT TRUE,
    display_order       INTEGER      NOT NULL DEFAULT 0,
    default_value       TEXT,
    lookup_table        VARCHAR(64),
    options             JSONB,
    validation_rules    JSONB,
    placeholder         VARCHAR(256),
    help_text           TEXT,
    unit                VARCHAR(32),
    category            VARCHAR(64),
    pii                 BOOLEAN      NOT NULL DEFAULT FALSE,
    encrypt_at_rest     BOOLEAN      NOT NULL DEFAULT FALSE,
    default_visibility  VARCHAR(32)  NOT NULL DEFAULT 'public',
    completion_weight   DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    is_active           BOOLEAN      NOT NULL DEFAULT TRUE,
    is_system           BOOLEAN      NOT NULL DEFAULT FALSE,
    created_by          VARCHAR(20),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pfd_section_order ON profile_field_definitions(section_id, display_order);

-- 4. Profile field values (with moderation)
CREATE TABLE IF NOT EXISTS profile_field_values (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    field_id            INTEGER      NOT NULL REFERENCES profile_field_definitions(id) ON DELETE CASCADE,
    value               TEXT,
    visibility          VARCHAR(32)  NOT NULL DEFAULT 'public',
    moderation_status   VARCHAR(16)  NOT NULL DEFAULT 'approved',
    moderated_by        INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    moderated_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, field_id)
);

CREATE INDEX IF NOT EXISTS idx_pfv_user_id     ON profile_field_values(user_id);
CREATE INDEX IF NOT EXISTS idx_pfv_field_id    ON profile_field_values(field_id);
CREATE INDEX IF NOT EXISTS idx_pfv_moderation  ON profile_field_values(moderation_status, updated_at);

-- 5. Profile value versions (audit trail)
CREATE TABLE IF NOT EXISTS profile_value_versions (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    field_id        INTEGER      REFERENCES profile_field_definitions(id) ON DELETE SET NULL,
    old_value       TEXT,
    new_value       TEXT,
    changed_by      INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    change_source   VARCHAR(32)  NOT NULL DEFAULT 'user',
    changed_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pvv_user_field  ON profile_value_versions(user_id, field_id);
CREATE INDEX IF NOT EXISTS idx_pvv_changed_at  ON profile_value_versions(changed_at);

-- 6. Profile search index (with full-text support)
CREATE TABLE IF NOT EXISTS profile_search_index (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    field_key       VARCHAR(64)      NOT NULL,
    value           TEXT,
    numeric_value   DOUBLE PRECISION,
    search_vector   TSVECTOR,
    updated_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_psi_user_field        ON profile_search_index(user_id, field_key);
CREATE INDEX IF NOT EXISTS idx_psi_field_value        ON profile_search_index(field_key, value);
CREATE INDEX IF NOT EXISTS idx_psi_field_numeric      ON profile_search_index(field_key, numeric_value);
CREATE INDEX IF NOT EXISTS idx_psi_search_vector      ON profile_search_index USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_psi_user_field_value   ON profile_search_index(user_id, field_key, value);

-- 7. Seed sections
INSERT INTO profile_sections (key, name, icon, display_order, completion_weight, is_system) VALUES
    ('basic_info',       'Basic Information',       'user',         10, 1.0, TRUE),
    ('personal_details', 'Personal Details',        'person',       20, 1.0, TRUE),
    ('lifestyle',        'Lifestyle',               'heart',        30, 0.8, TRUE),
    ('religion_caste',   'Religion & Caste',        'temple',       40, 0.6, TRUE),
    ('horoscope',        'Horoscope',               'star',         50, 0.3, TRUE),
    ('education_career', 'Education & Career',      'school',       60, 1.0, TRUE),
    ('family',           'Family Details',          'home',         70, 0.7, TRUE),
    ('location',         'Location & Visibility',   'map-pin',      80, 0.5, TRUE),
    ('about_me',         'About Me',                'edit',         90, 0.4, TRUE)
ON CONFLICT (key) DO NOTHING;

-- 8. Seed field definitions using lookup tables where applicable

-- basic_info: lookup-based fields (religion, education, occupation, marital_status, mother_tongue)
INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_required, is_searchable, display_order, lookup_table, is_system)
SELECT s.id, 'mother_tongue', 'Mother Tongue', 'lookup', FALSE, TRUE, 1, 'languages', TRUE FROM profile_sections s WHERE s.key = 'basic_info'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_required, is_searchable, display_order, lookup_table, is_system)
SELECT s.id, 'marital_status', 'Marital Status', 'select', FALSE, TRUE, 2, NULL, TRUE FROM profile_sections s WHERE s.key = 'basic_info'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_required, is_searchable, display_order, is_system)
SELECT s.id, 'college',   'College',   'text', FALSE, TRUE, 3, TRUE FROM profile_sections s WHERE s.key = 'basic_info'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_required, is_searchable, display_order, is_system)
SELECT s.id, 'workplace', 'Workplace', 'text', FALSE, TRUE, 4, TRUE FROM profile_sections s WHERE s.key = 'basic_info'
ON CONFLICT (key) DO NOTHING;

-- personal_details
INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_required, is_searchable, display_order, unit, validation_rules, is_system)
SELECT s.id, 'height_cm', 'Height', 'integer', FALSE, TRUE, 1, 'cm', '{"min_value":100,"max_value":250}'::jsonb, TRUE
FROM profile_sections s WHERE s.key = 'personal_details'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_searchable, display_order, is_system)
SELECT s.id, 'body_type', 'Body Type', 'select', FALSE, 2, TRUE FROM profile_sections s WHERE s.key = 'personal_details'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_searchable, display_order, is_system)
SELECT s.id, 'complexion', 'Complexion', 'select', FALSE, 3, TRUE FROM profile_sections s WHERE s.key = 'personal_details'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_searchable, display_order, is_system)
SELECT s.id, 'physical_status', 'Physical Status', 'select', FALSE, 4, TRUE FROM profile_sections s WHERE s.key = 'personal_details'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_searchable, display_order, is_system)
SELECT s.id, 'siblings', 'Siblings', 'text', FALSE, 5, TRUE FROM profile_sections s WHERE s.key = 'personal_details'
ON CONFLICT (key) DO NOTHING;

-- lifestyle
INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_searchable, display_order, is_system)
SELECT s.id, 'diet', 'Diet', 'select', TRUE, 1, TRUE FROM profile_sections s WHERE s.key = 'lifestyle'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_searchable, display_order, is_system)
SELECT s.id, 'drinking', 'Drinking', 'select', FALSE, 2, TRUE FROM profile_sections s WHERE s.key = 'lifestyle'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_searchable, display_order, is_system)
SELECT s.id, 'smoking', 'Smoking', 'select', FALSE, 3, TRUE FROM profile_sections s WHERE s.key = 'lifestyle'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, is_system)
SELECT s.id, 'favorite_color', 'Favorite Color', 'text', 4, TRUE FROM profile_sections s WHERE s.key = 'lifestyle'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, is_system)
SELECT s.id, 'favorite_sports', 'Favorite Sports', 'text', 5, TRUE FROM profile_sections s WHERE s.key = 'lifestyle'
ON CONFLICT (key) DO NOTHING;

-- religion_caste — lookup-based
INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_required, is_searchable, display_order, lookup_table, is_system)
SELECT s.id, 'religion', 'Religion', 'lookup', FALSE, TRUE, 1, 'religions', TRUE FROM profile_sections s WHERE s.key = 'religion_caste'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_searchable, display_order, lookup_table, is_system)
SELECT s.id, 'caste', 'Caste', 'lookup', TRUE, 2, 'castes', TRUE FROM profile_sections s WHERE s.key = 'religion_caste'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, is_system)
SELECT s.id, 'sub_caste', 'Sub Caste', 'text', 3, TRUE FROM profile_sections s WHERE s.key = 'religion_caste'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, is_system)
SELECT s.id, 'gothram', 'Gothram', 'text', 4, TRUE FROM profile_sections s WHERE s.key = 'religion_caste'
ON CONFLICT (key) DO NOTHING;

-- horoscope
INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, pii, is_system)
SELECT s.id, 'horoscope_match', 'Horoscope Match Required', 'boolean', 1, FALSE, TRUE FROM profile_sections s WHERE s.key = 'horoscope'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, pii, is_system)
SELECT s.id, 'nakshatra', 'Nakshatra', 'text', 2, FALSE, TRUE FROM profile_sections s WHERE s.key = 'horoscope'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, pii, is_system)
SELECT s.id, 'rashi', 'Rashi', 'text', 3, FALSE, TRUE FROM profile_sections s WHERE s.key = 'horoscope'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, pii, is_system)
SELECT s.id, 'dosham', 'Dosham', 'text', 4, FALSE, TRUE FROM profile_sections s WHERE s.key = 'horoscope'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, pii, encrypt_at_rest, is_system)
SELECT s.id, 'time_of_birth', 'Time of Birth', 'text', 5, TRUE, TRUE, TRUE FROM profile_sections s WHERE s.key = 'horoscope'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, pii, encrypt_at_rest, is_system)
SELECT s.id, 'place_of_birth', 'Place of Birth', 'text', 6, TRUE, TRUE, TRUE FROM profile_sections s WHERE s.key = 'horoscope'
ON CONFLICT (key) DO NOTHING;

-- education_career — lookup-based
INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_required, is_searchable, display_order, lookup_table, is_system)
SELECT s.id, 'education', 'Education', 'lookup', FALSE, TRUE, 1, 'educations', TRUE FROM profile_sections s WHERE s.key = 'education_career'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_required, is_searchable, display_order, lookup_table, is_system)
SELECT s.id, 'occupation', 'Occupation', 'lookup', FALSE, TRUE, 2, 'occupations', TRUE FROM profile_sections s WHERE s.key = 'education_career'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_searchable, display_order, is_system)
SELECT s.id, 'annual_income', 'Annual Income', 'text', TRUE, 3, TRUE FROM profile_sections s WHERE s.key = 'education_career'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, is_searchable, display_order, is_system)
SELECT s.id, 'employed_in', 'Employed In', 'text', TRUE, 4, TRUE FROM profile_sections s WHERE s.key = 'education_career'
ON CONFLICT (key) DO NOTHING;

-- family
INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, is_system)
SELECT s.id, 'family_type', 'Family Type', 'select', 1, TRUE FROM profile_sections s WHERE s.key = 'family'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, is_system)
SELECT s.id, 'family_values', 'Family Values', 'select', 2, TRUE FROM profile_sections s WHERE s.key = 'family'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, is_system)
SELECT s.id, 'father_occupation', 'Father Occupation', 'text', 3, TRUE FROM profile_sections s WHERE s.key = 'family'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, is_system)
SELECT s.id, 'mother_occupation', 'Mother Occupation', 'text', 4, TRUE FROM profile_sections s WHERE s.key = 'family'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, is_system)
SELECT s.id, 'brothers', 'Brothers', 'integer', 5, TRUE FROM profile_sections s WHERE s.key = 'family'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, is_system)
SELECT s.id, 'sisters', 'Sisters', 'integer', 6, TRUE FROM profile_sections s WHERE s.key = 'family'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, is_system)
SELECT s.id, 'family_location', 'Family Location', 'text', 7, TRUE FROM profile_sections s WHERE s.key = 'family'
ON CONFLICT (key) DO NOTHING;

-- location
INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, is_system)
SELECT s.id, 'profile_created_by', 'Profile Created By', 'select', 1, TRUE FROM profile_sections s WHERE s.key = 'location'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, default_visibility, display_order, is_system)
SELECT s.id, 'contact_visibility', 'Contact Visibility', 'select', 'matches_only', 2, TRUE
FROM profile_sections s WHERE s.key = 'location'
ON CONFLICT (key) DO NOTHING;

INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, is_system)
SELECT s.id, 'match_request_mode', 'Match Request Mode', 'boolean', 3, TRUE FROM profile_sections s WHERE s.key = 'location'
ON CONFLICT (key) DO NOTHING;

-- about_me
INSERT INTO profile_field_definitions (section_id, key, label, field_type, display_order, validation_rules, is_system)
SELECT s.id, 'about_family', 'About My Family', 'textarea', 1, '{"max_length":2000}'::jsonb, TRUE
FROM profile_sections s WHERE s.key = 'about_me'
ON CONFLICT (key) DO NOTHING;

COMMIT;
