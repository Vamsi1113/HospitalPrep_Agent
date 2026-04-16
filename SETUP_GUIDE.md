# 🚀 Setup Guide - PrepCare AI Agent

This guide walks you through setting up your PrepCare AI Agent application, from basic setup to full production configuration.

---

## 📋 Table of Contents

1. [Quick Start (No Credentials Needed)](#quick-start)
2. [Required Setup](#required-setup)
3. [Optional Integrations](#optional-integrations)
4. [Testing Your Setup](#testing-your-setup)
5. [Troubleshooting](#troubleshooting)

---

## 🎯 Quick Start (No Credentials Needed)

Your application works **immediately** without any API keys! It runs in mock mode with realistic fake data.

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Start the Server

```bash
python app.py
```

### Step 3: Open Your Browser

Navigate to: `http://localhost:5000`

**That's it!** The app is fully functional with:
- ✅ Mock hospital data
- ✅ Mock email notifications (console logs)
- ✅ Mock SMS notifications (console logs)
- ✅ Mock calendar events
- ✅ Template-based prep instructions (no LLM needed)

---

## 🔑 Required Setup

### 1. OpenRouter API Key (Recommended - FREE)

**Why?** Enables AI-enhanced prep instructions instead of templates.

**Cost:** FREE (uses free models with automatic fallback)

**Setup Steps:**

1. Go to https://openrouter.ai/
2. Sign up for a free account
3. Navigate to **Keys** section
4. Click **Create Key**
5. Copy your API key (starts with `sk-or-v1-...`)
6. Open your `.env` file
7. Replace the `OPENROUTER_API_KEY` value:

```env
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
```

**What happens without it?**
- App uses template-based messages (still works great!)
- No AI rewriting of prep instructions

---

## 🔌 Optional Integrations

Configure these only if you want real services instead of mock mode.

---

### 2. Geoapify Places API (Real Hospital Search)

#### Option A: Gmail API (Recommended for personal use)

**Why?** Send emails from your Gmail account.

**Cost:** FREE

**Setup Steps:**

1. Go to https://console.cloud.google.com/
2. Create/select a project
3. Enable **Gmail API**
4. Create a **Service Account**:
   - Go to **IAM & Admin** → **Service Accounts**
   - Click **Create Service Account**
   - Give it a name (e.g., "PrepCare Email")
   - Click **Create and Continue**
   - Skip role assignment
   - Click **Done**
5. Create credentials:
   - Click on your service account
   - Go to **Keys** tab
   - Click **Add Key** → **Create New Key**
   - Choose **JSON**
   - Download the JSON file
6. Save the JSON file to your project (e.g., `credentials/gmail-service-account.json`)
7. Add to `.env`:

```env
GMAIL_SENDER_ADDRESS=your-email@gmail.com
GMAIL_OAUTH_CREDENTIALS_JSON=credentials/gmail-service-account.json
```

#### Option B: SendGrid (Recommended for production)

**Why?** Professional email delivery service.

**Cost:** FREE tier - 100 emails/day

**Setup Steps:**

1. Go to https://sendgrid.com/
2. Sign up for a free account
3. Go to **Settings** → **API Keys**
4. Click **Create API Key**
5. Give it a name and select **Full Access**
6. Copy your API key
7. Verify a sender email:
   - Go to **Settings** → **Sender Authentication**
   - Verify a single sender email
8. Add to `.env`:

```env
SENDGRID_API_KEY=YOUR_API_KEY_HERE
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
```

**What happens without it?**
- Emails are logged to console (mock mode)

---

### 5. SMS Service (Choose ONE)

#### Option A: Fast2SMS (For India)

**Why?** Send SMS to Indian phone numbers.

**Cost:** FREE tier available

**Setup Steps:**

1. Go to https://www.fast2sms.com/
2. Sign up for a free account
3. Go to your **Dashboard**
4. Copy your **API Key**
5. Add to `.env`:

```env
FAST2SMS_API_KEY=YOUR_API_KEY_HERE
```

#### Option B: Twilio (International)

**Why?** Send SMS worldwide.

**Cost:** FREE trial with credits

**Setup Steps:**

1. Go to https://www.twilio.com/
2. Sign up for a free trial
3. Get your credentials from the dashboard:
   - **Account SID**
   - **Auth Token**
4. Get a Twilio phone number
5. Add to `.env`:

```env
TWILIO_ACCOUNT_SID=YOUR_ACCOUNT_SID
TWILIO_AUTH_TOKEN=YOUR_AUTH_TOKEN
TWILIO_PHONE_NUMBER=+1234567890
```

**What happens without it?**
- SMS are logged to console (mock mode)

---

### 6. Google Calendar (Appointment Scheduling)

**Why?** Create real calendar events for appointments.

**Cost:** FREE

**Setup Steps:**

1. Go to https://console.cloud.google.com/
2. Create/select a project
3. Enable **Google Calendar API**
4. Create a **Service Account** (same as Gmail steps 4-6)
5. Download the JSON key file
6. Get your Calendar ID:
   - Go to Google Calendar
   - Click settings (gear icon)
   - Select your calendar
   - Scroll to **Integrate calendar**
   - Copy the **Calendar ID**
7. Share your calendar with the service account:
   - In Calendar settings
   - Go to **Share with specific people**
   - Add the service account email (from JSON file)
   - Give **Make changes to events** permission
8. Add to `.env`:

```env
GOOGLE_CALENDAR_ID=your-calendar-id@group.calendar.google.com
GOOGLE_SERVICE_ACCOUNT_JSON=credentials/calendar-service-account.json
```

**What happens without it?**
- Calendar events are logged to console (mock mode)

---

### 7. Hospital Notifications

**Why?** Send booking notifications to hospital staff.

**Setup Steps:**

1. Add hospital email to `.env`:

```env
HOSPITAL_NOTIFY_EMAIL=appointments@hospital.com
```

**What happens without it?**
- No hospital notifications sent (patient still gets confirmation)

---

## 🧪 Testing Your Setup

### Test 1: Basic Functionality (No Credentials)

```bash
python app.py
```

Visit `http://localhost:5000` and:
1. Click a quick case (e.g., "Chest Pain")
2. Click "Analyze Symptoms"
3. Select a doctor and time slot
4. Click "Confirm & Book"

✅ Should work perfectly with mock data!

### Test 2: Voice Input (Browser Feature)

1. Click the microphone icon
2. Allow microphone access
3. Speak your symptoms
4. Watch fields auto-populate

✅ Works without any API keys (uses browser's Web Speech API)!

### Test 3: Real Hospital Search

**Prerequisites:** `GEOAPIFY_API_KEY` and `ORS_API_KEY` configured

1. Allow location access when prompted
2. Enter symptoms
3. Click "Analyze Symptoms"

✅ Should show real hospitals near you with travel times!

### Test 4: Email Delivery

**Prerequisites:** Gmail or SendGrid configured

1. Complete a booking
2. Enter your email address
3. Check your inbox

✅ Should receive confirmation email!

### Test 5: SMS Delivery

**Prerequisites:** Fast2SMS or Twilio configured

1. Complete a booking
2. Enter your phone number
3. Check your messages

✅ Should receive confirmation SMS!

---

## 🔧 Troubleshooting

### Issue: "Module not found" errors

**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: "OpenRouter API key invalid"

**Solution:**
- Check your API key starts with `sk-or-v1-`
- Verify it's copied correctly (no extra spaces)
- App will automatically fall back to templates if key is invalid

### Issue: "Gmail API authentication failed"

**Solution:**
- Verify JSON file path is correct
- Check service account has Gmail API enabled
- Make sure sender email matches your Gmail account

### Issue: "No hospitals found"

**Solution:**
- Check `GEOAPIFY_API_KEY` is set correctly
- Verify you haven't exceeded free tier limits (~3,000/day)
- Allow location access in your browser
- App will fall back to mock hospitals if API fails

### Issue: "Travel time not showing"

**Solution:**
- Check `ORS_API_KEY` is set correctly
- Verify you haven't exceeded free tier limits (2,000/day)
- Travel time is optional - everything else still works

### Issue: "Port 5000 already in use"

**Solution:**
```bash
# Find and kill the process
netstat -ano | findstr :5000
taskkill /PID <PID_NUMBER> /F

# Or use a different port
python app.py --port 5001
```

### Issue: "Database locked" error

**Solution:**
```bash
# Delete and recreate database
rm data/appointments.db
python app.py
```

---

## 📊 Configuration Summary

Here's what you need for different use cases:

### Minimum (Demo Mode)
- ✅ Nothing! Just run `python app.py`

### Basic AI Features
- ✅ `OPENROUTER_API_KEY` (free)

### Real Hospital Search
- ✅ `OPENROUTER_API_KEY` (free)
- ✅ `GEOAPIFY_API_KEY` (free tier)
- ✅ `ORS_API_KEY` (free tier)

### Full Production
- ✅ `OPENROUTER_API_KEY` (free)
- ✅ `GEOAPIFY_API_KEY` (free tier)
- ✅ `ORS_API_KEY` (free tier)
- ✅ Email service (Gmail or SendGrid)
- ✅ SMS service (Fast2SMS or Twilio)
- ✅ `GOOGLE_CALENDAR_ID` + service account
- ✅ `HOSPITAL_NOTIFY_EMAIL`

---

## 🎉 You're All Set!

Your PrepCare AI Agent is ready to use. Start with mock mode and add integrations as needed.

**Questions?** Check the main README.md or PROJECT_CONTEXT.md for more details.

**Happy coding! 🚀**
