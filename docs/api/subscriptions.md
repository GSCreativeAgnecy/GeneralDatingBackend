# Subscriptions & Payments

## Overview

Four payment processors are supported:

| Processor | Endpoint | Region |
|-----------|----------|--------|
| Stripe | `/subscriptions/checkout-session` | Global |
| Razorpay | `/subscriptions/order` | India |
| PayPal | `/subscriptions/paypal-order` | Global |
| Helcim | `/subscriptions/helcim-checkout` | North America |

## Plan System

Plans define capabilities and limits. Created/updated via admin API.

```json
{
    "name": "Premium Monthly",
    "price_paise": 49900,
    "duration_days": 30,
    "swipes_per_day": 200,
    "super_likes_per_day": 5,
    "messages": true,
    "see_who_liked_you": true
}
```

## Subscription Activation

1. Client creates order/checkout session with `plan_id`
2. User completes payment on provider's page
3. Client verifies payment via `/verify` or provider sends webhook
4. `_activate()` creates `Subscription` record, sets `user.is_premium = true`
5. Stacked subscriptions: new subscription starts after current one ends

## Webhook Security

All webhook endpoints verify signatures:

- **Stripe**: `stripe-signature` header + `construct_webhook_event()`
- **Razorpay**: `x-razorpay-signature` header + `verify_webhook_signature()`
- **PayPal**: `paypal-transmission-*` headers + verification API call
- **Helcim**: HMAC-SHA256 comparison of `x-helcim-signature`

## Plan Endpoints (Public)

### GET `/subscriptions/plans`

List all active plans with features.

### GET `/subscriptions/me`

Current user's active subscription (returns free tier if none).

## Web Checkout (No JWT)

For web checkout flow where the user may not be logged in:

- `POST /subscriptions/web-order` — creates order with phone + OTP auth
- `POST /subscriptions/web-verify` — verifies payment and creates/activates account
