# Changelog

## [Unreleased]

### Added
- Modular profile system v2 (sections, lookup tables, versioning, moderation)
- Internal documentation portal at `/internal-docs`
- Profile completion scoring with weighted fields
- Profile value versioning (audit trail)
- Moderation workflow for profile field values
- Lookup tables for religions, castes, occupations, educations, languages
- Full-text search index with PostgreSQL TSVECTOR
- Request body size limiting middleware
- Security headers middleware
- Hindi localization support for labels

### Changed
- User model slimmed with legacy columns retained for backward compatibility
- Rate limiter: thread-safe with periodic cleanup
- CORS: explicit methods and headers
- Database migration: SQL identifier validation before ALTER TABLE
- OTP: only exposed in response when DEBUG=true AND SMS fails

### Fixed
- Plan creation bug (`first_name` → `name` column mismatch)
- User `name` @property causing AttributeError in SQL queries
- User creation bug (missing `first_name` column in OTP verify)
- Removed dead `name` properties from non-User models
- JWT secret: validation and auto-generation in DEBUG mode

## [1.0.0] - Initial Release

- Phone OTP authentication + email/password login
- JWT access + refresh tokens with token rotation
- Profile management (photos, languages, preferences)
- Swipe-based discovery with daily limits
- Mutual matching with notifications
- In-app messaging with women-first rule
- WebSocket typing indicators
- Premium subscriptions (Razorpay, Stripe, PayPal, Helcim)
- Family/friend profile sharing
- Admin dashboard with user/plan/report management
- Dummy data generation
- Docker + Docker Compose deployment
