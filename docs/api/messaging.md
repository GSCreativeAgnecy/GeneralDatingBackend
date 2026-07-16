# Messaging

## Overview

In-app messaging between matched users. Accessible only within active matches.

## Women-First Rule

In male-female matches where no messages exist yet, the male user **cannot** send the first message. The female user must initiate.

```json
// GET /matches/123/women-first-status
{"can_send": false, "reason": "Women must send the first message"}
```

This rule applies only to male-female pairings. Same-gender matches and matches with existing messages are unrestricted.

## Endpoints

### GET `/matches/{id}/messages`

Retrieve paginated messages for a match. Messages from the other user are auto-marked as read.

### POST `/matches/{id}/messages`

Send a message.

```json
{"message_type": "text", "content": "Hello!"}
```

### PUT `/matches/{id}/messages/read`

Mark all messages from the other user as read.

## Message Model

| Field | Type | Notes |
|-------|------|-------|
| id | INTEGER | PK |
| match_id | INTEGER | FK → matches |
| sender_id | INTEGER | FK → users |
| message_type | VARCHAR | Default "text" |
| content | TEXT | Message body |
| is_read | BOOLEAN | Read receipt |
| created_at | TIMESTAMPTZ | Auto-generated |

## WebSocket

Real-time typing indicators via WebSocket at `ws://host/ws`:

```json
// Client → Server
{"type": "typing_start", "data": {"match_id": 123}}

// Server → Client
{"type": "typing_ack", "data": {"match_id": 123}}
```

Connection requires JWT authentication via the first message after handshake. Keepalive via `ping`/`pong` messages.
