# 📱 Twilio SMS Setup Guide

## Step-by-Step Instructions

### Step 1: Create Twilio Account

1. Go to **https://www.twilio.com/**
2. Click **Sign up** (top right)
3. Fill in your details:
   - Email address
   - Password
   - First name, Last name
4. Click **Start your free trial**
5. **Verify your email** (check inbox)
6. **Verify your phone number** (you'll receive a code via SMS)

---

### Step 2: Get Your Account Credentials

After signing in, you'll see your **Twilio Console Dashboard**.

#### Get Account SID and Auth Token:

1. On the dashboard, look for the **Account Info** section
2. You'll see:
   - **Account SID** - Copy this (starts with `AC...`)
   - **Auth Token** - Click "Show" then copy it

**Screenshot location:**
```
Dashboard → Account Info (right side)
├── Account SID: ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
└── Auth Token: [Show] → Copy the token
```

---

### Step 3: Get a Twilio Phone Number

1. In the left sidebar, click **# Phone Numbers**
2. Click **Manage** → **Buy a number**
3. Or click the **Get a trial number** button (faster for testing)
4. Select your country (e.g., United States)
5. Click **Search**
6. Choose a number with **SMS** capability
7. Click **Buy** (it's free for trial)
8. Confirm the purchase

**Your trial number will look like:** `+1234567890`

---

### Step 4: Add to Your .env File

Open your `.env` file and add these three values:

```env
# Twilio SMS Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
```

**Example:**
```env
TWILIO_ACCOUNT_SID=AC1234567890abcdef1234567890abcd
TWILIO_AUTH_TOKEN=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
TWILIO_PHONE_NUMBER=+15551234567
```

---

### Step 5: Verify Phone Numbers (Trial Account Only)

⚠️ **Important for Trial Accounts:**

Trial accounts can only send SMS to **verified phone numbers**.

#### To verify a phone number:

1. Go to **Phone Numbers** → **Manage** → **Verified Caller IDs**
2. Click **Add a new Caller ID**
3. Enter the phone number you want to test with
4. Click **Call Me** or **Text Me**
5. Enter the verification code you receive
6. Now you can send SMS to this number!

**Note:** Once you upgrade to a paid account, you can send to any number.

---

### Step 6: Test Your Setup

Restart your server:
```bash
python app.py
```

Then test by:
1. Completing a booking in your app
2. Enter your **verified phone number**
3. Check your phone for the SMS!

---

## 🎁 Trial Account Limits

Your free trial includes:
- ✅ **$15.50 in free credit**
- ✅ SMS to verified numbers only
- ✅ Voice calls to verified numbers
- ✅ Full API access
- ⚠️ Messages include "Sent from your Twilio trial account"

---

## 💰 Pricing (After Trial)

When you upgrade:
- **SMS:** ~$0.0075 per message (US)
- **Phone number:** $1/month
- **No monthly fees** - pay as you go

---

## 🔍 Where to Find Everything

### Account SID & Auth Token:
```
Twilio Console → Dashboard → Account Info (right panel)
```

### Phone Number:
```
Twilio Console → # Phone Numbers → Manage → Active numbers
```

### Verify Phone Numbers:
```
Twilio Console → # Phone Numbers → Manage → Verified Caller IDs
```

### Usage & Billing:
```
Twilio Console → Monitor → Usage
```

---

## 🆘 Troubleshooting

### Issue: "Unable to create record: The number is unverified"

**Solution:**
- You're using a trial account
- Verify the recipient phone number first
- Go to: Phone Numbers → Verified Caller IDs → Add new

### Issue: "Authentication Error"

**Solution:**
- Check Account SID starts with `AC`
- Verify Auth Token is correct (no extra spaces)
- Restart your server after updating `.env`

### Issue: "Invalid phone number format"

**Solution:**
- Use E.164 format: `+[country code][number]`
- Example: `+15551234567` (US)
- Example: `+919876543210` (India)

### Issue: "Messages not sending"

**Solution:**
1. Check your Twilio balance (trial credit)
2. Verify the phone number is verified (trial accounts)
3. Check Twilio Console → Monitor → Logs for errors

---

## 📊 Quick Reference

| Item | Format | Example |
|------|--------|---------|
| Account SID | `AC` + 32 chars | `AC1234567890abcdef...` |
| Auth Token | 32 characters | `a1b2c3d4e5f6g7h8...` |
| Phone Number | E.164 format | `+15551234567` |

---

## ✅ Setup Checklist

- [ ] Created Twilio account
- [ ] Verified email
- [ ] Verified phone number
- [ ] Got Account SID
- [ ] Got Auth Token
- [ ] Got Twilio phone number
- [ ] Added all three to `.env` file
- [ ] Verified test phone number (trial only)
- [ ] Restarted server
- [ ] Tested SMS sending

---

## 🎉 You're Done!

Your Twilio SMS integration is ready. Test it by completing a booking with a verified phone number!

**Need help?** Check Twilio docs: https://www.twilio.com/docs/sms
