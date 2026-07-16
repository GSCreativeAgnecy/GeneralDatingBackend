# Admin API

## Authentication

Admins are identified by phone number whitelist in `ADMIN_PHONES` environment variable. All admin endpoints require `get_current_admin` dependency which checks the authenticated user's phone number against this list.

## Dashboard

### GET `/admin/dashboard`

Aggregate statistics: total users, active today, matches today, pending reports, premium count, photos, swipes, messages, waitlist.

## User Management

| Endpoint | Purpose |
|----------|---------|
| `GET /admin/users` | Paginated list with search and sorting |
| `GET /admin/users/{id}` | Full user detail with photos and languages |
| `GET /admin/users/{id}/stats` | Activity stats (swipes, matches, messages, reports) |
| `GET /admin/users/{id}/swipes` | User swipe history |
| `GET /admin/users/{id}/matches` | User match history |
| `GET /admin/users/{id}/messages` | User message history |
| `PATCH /admin/users/{id}` | Quick update (active, premium, verified) |
| `PUT /admin/users/{id}` | Full profile edit |
| `POST /admin/users` | Create new user |
| `DELETE /admin/users/{id}` | Delete user (cascading) |
| `POST /admin/users/{id}/reset-password` | Set new password |
| `POST /admin/users/{id}/assign-plan` | Assign premium plan |
| `POST /admin/users/{id}/remove-plan` | Remove premium status |

## Import/Export

- `GET /admin/users/export?fmt=json|csv` — export all users
- `POST /admin/users/import` — import users from JSON file (skips duplicates)

## Settings Dashboard

### GET/PUT `/admin/settings`

White-label branding, payment processor configuration, OTP providers, SMTP settings — all managed through the admin API with runtime `AppSetting` updates.

Settings include:
- Branding (app name, colors)
- Currency (INR, USD, EUR, etc.)
- Payment processors (Stripe, Razorpay, PayPal, Helcim)
- OTP providers (Twilio, Android SMS)
- SMTP configuration

## Report & Moderation

### GET `/admin/reports`

Paginated report list with reporter/reported names.

### POST `/admin/reports/{id}/action`

```json
{"action": "ban"}  // or "dismiss"
```

Banning sets `user.is_active = false`. Both actions delete the report record.

## Profile Field Management

Admins can manage profile sections and field definitions via `/profile/v2/admin/*` endpoints, including lookup table values.
