# .env File Setup Guide

## Quick Start: You Don't Need Anything! 🎉

The `.env` file has been created and **the system works perfectly without any credentials**. All services run in "mock mode" which means:

- ✅ Calendar shows realistic fake appointment slots
- ✅ SMS messages are logged to console
- ✅ Emails are logged to console
- ✅ Everything works for testing and development

## Just Run It

```bash
# Install dependencies
pip install -r requirements.txt

# Start the app (no configuration needed!)
python app.py

# Open browser to http://localhost:5000
```

You'll see mock mode messages in the console like:
```
[CalendarService MOCK] Event created: Surgery - John Doe → MOCK_EVT_20260409123456
[SMSService MOCK] SMS sent to +1234567890
[EmailService MOCK] Email sent to john@example.com
```

## When to Add Credentials (Optional)

Add credentials to `.env` only if you want to use **real services** instead of mock mode:

### 1. OpenRouter API (Optional - FREE!)

**What it does**: Rewrites messages in a friendly tone using FREE Google Gemini model  
**Without it**: Uses template-based messages (works great!)  
**Cost**: **COMPLETELY FREE** - No charges, unlimited usage on free tier  

To enable:
```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Get a FREE key at: https://openrouter.ai/keys (no credit card needed!)

**Model used**: `google/gemma-2-9b-it:free` (100% free, no limits)

### 2. Google Calendar (Optional)
**What it does**: Shows real available slots from your Google Calendar  
**Without it**: Generates realistic fake slots  
**Cost**: Free  

To enable:
```env
GOOGLE_CALENDAR_ID=your-calendar-id@group.calendar.google.com
GOOGLE_SERVICE_ACCOUNT_JSON=path/to/service-account-key.json
```

Setup steps:
1. Go to https://console.cloud.google.com/
2. Create project → Enable Calendar API
3. Create service account → Download JSON key
4. Share your calendar with the service account email

### 3. Twilio SMS (Optional)
**What it does**: Sends real SMS messages to patients  
**Without it**: Logs SMS to console  
**Cost**: ~$0.0075 per SMS (free trial available)  

To enable:
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

Get credentials at: https://www.twilio.com/ (free trial includes $15 credit)

### 4. SendGrid Email (Optional)
**What it does**: Sends real emails to patients  
**Without it**: Logs emails to console  
**Cost**: Free tier (100 emails/day)  

To enable:
```env
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
```

Get API key at: https://sendgrid.com/ (free account)

## Current .env File Status

Your `.env` file is configured for **mock mode** (all credentials empty):

```env
OPENAI_API_KEY=
# GOOGLE_CALENDAR_ID=
# TWILIO_ACCOUNT_SID=
# SENDGRID_API_KEY=
```

This is perfect for:
- ✅ Local development
- ✅ Testing
- ✅ Demos
- ✅ Learning the system

## How to Add Credentials

Simply uncomment the lines and add your credentials:

**Before** (mock mode):
```env
# TWILIO_ACCOUNT_SID=
# TWILIO_AUTH_TOKEN=
```

**After** (real SMS):
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
```

Then restart the Flask app:
```bash
# Stop the app (Ctrl+C)
# Start it again
python app.py
```

## Checking What Mode You're In

When you start the app, check the console:

**Mock Mode** (no credentials):
```
[CalendarService] Using mock calendar mode
[SMSService] Using mock SMS mode
[EmailService] Using mock email mode
```

**Real Services** (with credentials):
```
[CalendarService] Connected to Google Calendar
[SMSService] Connected to Twilio
[EmailService] Connected to SendGrid
```

## Security Notes

- ✅ `.env` is already in `.gitignore` (won't be committed to git)
- ✅ Never share your `.env` file
- ✅ Never commit credentials to version control
- ✅ Use environment variables in production

## Recommended Setup for Different Environments

### Local Development (Current Setup)
```env
OPENAI_API_KEY=
# All other services commented out
```
**Result**: Everything works in mock mode, no costs, no setup needed

### Testing with Real AI
```env
OPENAI_API_KEY=sk-proj-your-key-here
# Other services still in mock mode
```
**Result**: AI-enhanced messages, other services still mock

### Full Production Setup
```env
OPENAI_API_KEY=sk-proj-your-key-here
GOOGLE_CALENDAR_ID=your-calendar@group.calendar.google.com
GOOGLE_SERVICE_ACCOUNT_JSON=path/to/key.json
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
```
**Result**: All real services, production-ready

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### Services not working
Check console for mock mode messages. If you see `[ServiceName MOCK]`, it's working correctly.

### Want to switch back to mock mode
Just comment out or remove the credentials from `.env` and restart the app.

## Summary

✅ **Current Status**: `.env` file created and ready  
✅ **Configuration**: Mock mode (no credentials needed)  
✅ **Next Step**: Just run `python app.py`  
✅ **Optional**: Add credentials later if you want real services  

**You're all set to start testing!** 🚀
