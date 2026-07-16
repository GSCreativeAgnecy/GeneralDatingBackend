-- Recommended database indexes for Brownies Dating App
-- Run with: psql -d brownies -f 001_add_performance_indexes.sql

BEGIN;

-- Discovery feed filtering: optimize the core profile discovery query
CREATE INDEX IF NOT EXISTS idx_users_discovery
    ON users(profile_complete, is_active)
    WHERE profile_complete = true AND is_active = true;

-- Gender filter in discovery (preferences-based)
CREATE INDEX IF NOT EXISTS idx_users_gender
    ON users(gender);

-- Intent filter in discovery
CREATE INDEX IF NOT EXISTS idx_users_intent
    ON users(intent);

-- Swipe daily count queries (get_stats, create_swipe limits)
CREATE INDEX IF NOT EXISTS idx_swipes_swiper_date
    ON swipes(swiper_id, created_at);

-- Swipe mutual check (match creation logic)
CREATE INDEX IF NOT EXISTS idx_swipes_swiper_swiped
    ON swipes(swiper_id, swiped_id);

-- Message retrieval by match (chat loading)
CREATE INDEX IF NOT EXISTS idx_messages_match_date
    ON messages(match_id, created_at);

-- Message sent lookup by sender
CREATE INDEX IF NOT EXISTS idx_messages_sender
    ON messages(sender_id);

-- Notification queries by user + unread status
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
    ON notifications(user_id, is_read);

-- Notification ordering
CREATE INDEX IF NOT EXISTS idx_notifications_user_date
    ON notifications(user_id, created_at);

-- Blocks/reports lookup by reporter
CREATE INDEX IF NOT EXISTS idx_blocks_reporter_type
    ON blocks_reports(reporter_id, type);

-- Blocks/reports exclusion in discovery
CREATE INDEX IF NOT EXISTS idx_blocks_reporter_reported
    ON blocks_reports(reporter_id, reported_id);

-- Subscription active lookup
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_active
    ON subscriptions(user_id, is_active)
    WHERE is_active = true;

-- OTP records cleanup and rate limit queries
CREATE INDEX IF NOT EXISTS idx_otp_phone_expires
    ON otp_records(phone, expires_at);

-- User city index for discovery filtering (already exists in model, reinforced here)
CREATE INDEX IF NOT EXISTS idx_users_city_active
    ON users(city)
    WHERE is_active = true;

-- Family share token lookup (public profile access)
CREATE INDEX IF NOT EXISTS idx_family_shares_token
    ON family_shares(access_token);

-- Match ordering for chat lists
CREATE INDEX IF NOT EXISTS idx_matches_active_date
    ON matches(is_active, matched_at)
    WHERE is_active = true;

COMMIT;
