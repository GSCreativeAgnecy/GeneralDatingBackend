# Matching Engine

## Discovery Feed

`GET /discovery` returns profiles filtered by:

- **Preferences**: age range, gender, intent, city
- **Exclusions**: already swiped, blocked, or blocked-by users
- **Active users only**: `is_active = true`, `profile_complete = true`
- **Distance**: filtered by `max_distance_km`, sorted nearest-first

Response includes up to 20 profiles per request with photos and distance.

## Swipe Mechanics

### POST `/discovery/swipes`

```json
{"swiped_id": 42, "direction": "like"}
```

Directions: `like`, `pass`, `super_like`

### Daily Limits

| Plan | Likes/Day | Super Likes/Day |
|------|-----------|-----------------|
| Free | 50 | 1 |
| Premium Monthly | 200 | 5 |
| Custom | Plan-defined | Plan-defined |

Limits reset at midnight UTC.

## Match Creation

When user A swipes right on user B and user B has already swiped right on user A:

1. A `Match` record is created with `user1_id < user2_id` enforced
2. Both users receive a `Notification` (type: `match`)
3. The swipe response includes `{"matched": true, "match_id": 123}`

## Premium Features

| Feature | Free | Premium |
|---------|------|---------|
| See who liked you | Blurred | Full profile |
| Undo last swipe | Not available | Available |
| Match detail view | Not available | Available |

## Blocking

Blocking a user (`POST /blocks`) automatically deactivates any mutual match.
