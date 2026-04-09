# Quick Reference Card

## ✅ What You Have Now

- `.env` file created and configured for mock mode
- All services work without credentials
- System ready to run immediately

## 🚀 Start the App

```bash
python app.py
```

Then open: http://localhost:5000

## 📋 What's in Your .env File

```env
OPENROUTER_API_KEY=                # Empty = mock mode ✅ (FREE model available!)
# GOOGLE_CALENDAR_ID=              # Commented = mock mode ✅
# TWILIO_ACCOUNT_SID=              # Commented = mock mode ✅
# SENDGRID_API_KEY=                # Commented = mock mode ✅
```

## 🎯 Current Configuration

| Service | Status | What It Does |
|---------|--------|--------------|
| OpenRouter (Gemini) | Mock Mode | Uses templates (FREE AI available!) |
| Calendar | Mock Mode | Shows fake slots |
| SMS | Mock Mode | Logs to console |
| Email | Mock Mode | Logs to console |

## 📝 To Add Real Services (Optional)

### OpenRouter (FREE AI-enhanced messages)
```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```
Get FREE key at: https://openrouter.ai/keys (no credit card needed!)  
Model: google/gemma-2-9b-it:free (completely free, unlimited)

### Google Calendar (real scheduling)
```env
GOOGLE_CALENDAR_ID=your-calendar@group.calendar.google.com
GOOGLE_SERVICE_ACCOUNT_JSON=path/to/key.json
```

### Twilio (real SMS)
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
```

### SendGrid (real email)
```env
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
```

## 🧪 Test the New Features

### Get Available Slots
```bash
curl -X POST http://localhost:5000/api/slots \
  -H "Content-Type: application/json" \
  -d '{"appointment_type": "Surgery"}'
```

### Book Appointment
```bash
curl -X POST http://localhost:5000/api/book \
  -H "Content-Type: application/json" \
  -d '{
    "slot": {"start": "2026-04-15T09:00:00", "end": "2026-04-15T09:30:00"},
    "patient_name": "John Doe",
    "appointment_type": "Surgery"
  }'
```

### Patient Chat
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What should I bring?",
    "session_id": "test123"
  }'
```

### Post-Procedure Recovery
```bash
curl -X POST http://localhost:5000/api/post-procedure \
  -H "Content-Type: application/json" \
  -d '{"procedure": "Surgery", "patient_name": "John Doe"}'
```

## 📚 Documentation Files

- `ENV_SETUP_GUIDE.md` - Detailed .env setup instructions
- `NEXT_STEPS.md` - Testing guide with examples
- `UPGRADE_COMPLETE_SUMMARY.md` - Technical details
- `.env.example` - Template with all options

## 🔍 Check What Mode You're In

Look for these console messages when starting the app:

**Mock Mode** (current):
```
[CalendarService] Using mock calendar mode
[SMSService] Using mock SMS mode
[EmailService] Using mock email mode
```

**Real Services** (after adding credentials):
```
[CalendarService] Connected to Google Calendar
[SMSService] Connected to Twilio
[EmailService] Connected to SendGrid
```

## ⚡ Quick Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start app
python app.py

# Run tests
pytest

# Check for errors
python -c "import app; print('OK')"
```

## 🎉 You're Ready!

Everything is configured and ready to run. No credentials needed for testing.

**Next step**: `python app.py`
