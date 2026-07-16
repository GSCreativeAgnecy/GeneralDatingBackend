# Troubleshooting

## Common Issues

### "JWT_SECRET must be at least 32 characters"

Set a proper secret in `.env`:

```
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(64))")
```

### "Could not connect to database"

1. Verify PostgreSQL is running
2. Check `DATABASE_URL` in `.env`
3. Ensure database exists: `createdb ardhang`
4. Check firewall / Docker networking

### "Module not found: core"

Run from the `src/` directory:

```bash
cd src
uvicorn main:app --reload
```

### "No admin accounts configured"

Set `ADMIN_PHONES` in `.env`:

```
ADMIN_PHONES=+919999999999
```

Then login with that phone number via OTP — you'll have admin access.

### "bcrypt version conflict"

The project pins `bcrypt<4.1`. If you encounter issues:

```bash
pip install bcrypt==4.0.1
```

### Docker: tables not created on first run

The `entrypoint.sh` runs `python seed.py` which calls `init_db()`. If tables don't exist:

```bash
docker-compose exec api python seed.py
```

### OTP not being received

1. Check `PREFERRED_OTP_PROVIDER` configuration
2. For Twilio: verify `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE`
3. For Android SMS: verify `ANDROID_SMS_GATEWAY_URL` and API key
4. Without a provider: set `DEBUG=true` to see OTP in response (development only)

### CORS errors

Configure `CORS_ORIGINS` to include your frontend URL:

```
CORS_ORIGINS=http://localhost:5173,https://app.yourdomain.com
```

### Rate limit exceeded (429)

Wait 60 seconds or increase the limit in `middleware/rate_limit.py`. Production should use Redis-based limiting.

### Profile fields not showing in v2 API

Run the migration or restart the seed:

```bash
python seed.py
```
