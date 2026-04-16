# ⚡ Quick Start Guide

## 🎯 Start in 3 Steps (No Setup Required!)

### 1️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 2️⃣ Start Server
```bash
python app.py
```

### 3️⃣ Open Browser
```
http://localhost:5000
```

**✅ That's it! Your app is running with mock data.**

---

## 🔑 Add Your API Keys (Optional)

Your app already has **one API key configured**:

### ✅ Already Configured
- **OpenRouter API** - AI-enhanced prep instructions (FREE)
  - Your key: `sk-or-v1-8570...96d0`
  - Status: ✅ Active

### 🔌 Optional Integrations

Add these to `.env` file only if you want real services:

#### 1. Real Hospital Search (FREE)
```env
GEOAPIFY_API_KEY=your_key_here
ORS_API_KEY=your_key_here
```
**Get keys:**
- Geoapify Places: https://www.geoapify.com/ (~3,000 requests/day free)
- OpenRouteService: https://openrouteservice.org/ (2,000 requests/day free)

#### 2. Email Notifications (Choose ONE)

**Option A: Gmail (Personal)**
```env
GMAIL_SENDER_ADDRESS=your-email@gmail.com
GMAIL_OAUTH_CREDENTIALS_JSON=path/to/credentials.json
```

**Option B: SendGrid (Professional)**
```env
SENDGRID_API_KEY=your_key_here
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
```

#### 3. SMS Notifications (Choose ONE)

**Option A: Fast2SMS (India)**
```env
FAST2SMS_API_KEY=your_key_here
```

**Option B: Twilio (International)**
```env
TWILIO_ACCOUNT_SID=your_sid_here
TWILIO_AUTH_TOKEN=your_token_here
TWILIO_PHONE_NUMBER=+1234567890
```

#### 4. Calendar Integration
```env
GOOGLE_CALENDAR_ID=your-calendar-id@group.calendar.google.com
GOOGLE_SERVICE_ACCOUNT_JSON=path/to/credentials.json
```

#### 5. Hospital Notifications
```env
HOSPITAL_NOTIFY_EMAIL=appointments@hospital.com
```

---

## 📱 What Works Without Any Setup?

Everything! Your app runs in **mock mode** with:

| Feature | Mock Mode | Real Mode |
|---------|-----------|-----------|
| Voice Input | ✅ Browser API | ✅ Browser API |
| Geolocation | ✅ Browser API | ✅ Browser API |
| AI Prep Instructions | ✅ Active (OpenRouter) | ✅ Active |
| Hospital Search | ✅ Fake data | ⚙️ Needs Geoapify |
| Travel Time | ❌ Not shown | ⚙️ Needs ORS API |
| Email Confirmations | ✅ Console logs | ⚙️ Needs Gmail/SendGrid |
| SMS Confirmations | ✅ Console logs | ⚙️ Needs Fast2SMS/Twilio |
| Calendar Events | ✅ Console logs | ⚙️ Needs Google Calendar |

---

## 🧪 Test Your Setup

### Test 1: Basic Flow (No credentials needed)
1. Open `http://localhost:5000`
2. Click "Chest Pain" quick case
3. Click "Analyze Symptoms"
4. Select a doctor and time slot
5. Click "Confirm & Book"

✅ Should complete successfully!

### Test 2: Voice Input (No credentials needed)
1. Click microphone icon 🎤
2. Allow microphone access
3. Say: "I have chest pain and shortness of breath"
4. Watch fields auto-populate

✅ Should transcribe and extract info!

### Test 3: Real Hospitals (Needs Geoapify + ORS)
1. Allow location access
2. Enter symptoms
3. Click "Analyze Symptoms"

✅ Should show real nearby hospitals with travel times!

---

## 🆘 Common Issues

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Port 5000 already in use"
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:5000 | xargs kill -9
```

### "OpenRouter API error"
- App automatically falls back to templates
- Everything still works!

### "No hospitals found"
- App automatically uses mock data
- Everything still works!

---

## 📚 Need More Details?

- **Full Setup Guide:** See `SETUP_GUIDE.md`
- **Project Overview:** See `PROJECT_CONTEXT.md`
- **API Details:** See `API_AND_DATA_SOURCES_ANALYSIS.md`

---

## 🎉 You're Ready!

Your app is **fully functional** right now. Add integrations only when you need them.

**Start the server and try it out! 🚀**
