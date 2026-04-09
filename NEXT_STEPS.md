# Next Steps: Testing and Using the Upgraded System

## What's Been Completed

The backend for the full patient journey system is now complete:
- ✅ Calendar scheduling (Google Calendar + mock)
- ✅ SMS notifications (Twilio + mock)
- ✅ Email delivery (SendGrid + mock)
- ✅ Patient Q&A chat
- ✅ Post-procedure recovery plans
- ✅ 5 new API endpoints
- ✅ Session state management

## Quick Start: Test in Mock Mode

The system works immediately without any credentials:

```bash
# 1. Install new dependencies
pip install -r requirements.txt

# 2. Start the Flask server
python app.py

# 3. Open browser to http://localhost:5000
```

All services will run in mock mode (console logging) automatically.

## Testing the New API Endpoints

### 1. Get Available Slots

```bash
curl -X POST http://localhost:5000/api/slots \
  -H "Content-Type: application/json" \
  -d '{
    "appointment_type": "Surgery",
    "preferred_date": "2026-04-15",
    "duration_minutes": 30
  }'
```

Expected response:
```json
{
  "error": false,
  "slots": [
    {
      "start": "2026-04-15T09:00:00",
      "end": "2026-04-15T09:30:00",
      "start_formatted": "Tuesday, 15 Apr 2026 at 09:00 AM",
      "doctor": "Dr. Mehta (Surgery)",
      "location": "Main Clinic, Floor 2",
      "slot_id": "SLOT_202604150900"
    }
  ]
}
```

### 2. Book Appointment

```bash
curl -X POST http://localhost:5000/api/book \
  -H "Content-Type: application/json" \
  -d '{
    "slot": {
      "start": "2026-04-15T09:00:00",
      "end": "2026-04-15T09:30:00",
      "start_formatted": "Tuesday, 15 Apr 2026 at 09:00 AM",
      "doctor": "Dr. Mehta",
      "location": "Main Clinic"
    },
    "patient_name": "John Doe",
    "appointment_type": "Surgery",
    "procedure": "Knee Surgery",
    "email": "john@example.com",
    "phone": "+1234567890"
  }'
```

Expected response:
```json
{
  "error": false,
  "event_id": "MOCK_EVT_20260409123456",
  "message": "Appointment booked successfully"
}
```

Check console for mock SMS and email logs.

### 3. Patient Chat

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What should I bring to my appointment?",
    "session_id": "test_session_123",
    "appointment_type": "Surgery",
    "procedure": "Knee Surgery"
  }'
```

Expected response:
```json
{
  "error": false,
  "response": "For your surgery appointment, please bring...",
  "chat_history": [
    {
      "role": "patient",
      "content": "What should I bring to my appointment?",
      "timestamp": "2026-04-09T12:00:00"
    },
    {
      "role": "agent",
      "content": "For your surgery appointment, please bring...",
      "timestamp": "2026-04-09T12:00:01"
    }
  ]
}
```

### 4. Post-Procedure Recovery

```bash
curl -X POST http://localhost:5000/api/post-procedure \
  -H "Content-Type: application/json" \
  -d '{
    "procedure": "Knee Surgery",
    "patient_name": "John Doe",
    "email": "john@example.com"
  }'
```

Expected response:
```json
{
  "error": false,
  "recovery_plan": {
    "procedure": "knee surgery",
    "instructions": "POST-PROCEDURE RECOVERY INSTRUCTIONS\n\nREST PERIOD: 24-48 hours...",
    "activity_restrictions": [
      "No driving for 24 hours",
      "No heavy lifting (>10 lbs) for 1 week"
    ],
    "warning_signs": [
      "Fever over 101°F",
      "Excessive bleeding"
    ],
    "follow_up_needed": true,
    "follow_up_timeframe": "1-2 weeks"
  }
}
```

### 5. Cancel Appointment

```bash
curl -X POST http://localhost:5000/api/cancel \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "MOCK_EVT_20260409123456",
    "phone": "+1234567890",
    "appointment_datetime": "Tuesday, 15 Apr 2026 at 09:00 AM"
  }'
```

Expected response:
```json
{
  "error": false,
  "message": "Appointment cancelled successfully"
}
```

## Configuring Real Services (Optional)

### Google Calendar Setup

1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable Google Calendar API
4. Create a service account
5. Download JSON key file
6. Share your calendar with the service account email
7. Update `.env`:
   ```
   GOOGLE_CALENDAR_ID=your-calendar-id@group.calendar.google.com
   GOOGLE_SERVICE_ACCOUNT_JSON=path/to/service-account-key.json
   ```

### Twilio SMS Setup

1. Go to https://www.twilio.com/
2. Sign up for free trial
3. Get Account SID, Auth Token, and phone number
4. Update `.env`:
   ```
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=+1234567890
   ```

### SendGrid Email Setup

1. Go to https://sendgrid.com/
2. Sign up for free account
3. Create API key in Settings > API Keys
4. Verify sender email
5. Update `.env`:
   ```
   SENDGRID_API_KEY=your_api_key
   SENDGRID_FROM_EMAIL=noreply@yourdomain.com
   ```

## Verifying Mock Mode

When running without credentials, you should see console output like:

```
[CalendarService MOCK] Event created: Surgery - John Doe → MOCK_EVT_20260409123456

[SMSService MOCK] SMS sent to +1234567890
Message ID: MOCK_SMS_20260409123456
Message: Appointment Confirmed!...

[EmailService MOCK] Email sent to john@example.com
Subject: Appointment Confirmed - Tuesday, 15 Apr 2026 at 09:00 AM
Message ID: MOCK_EMAIL_20260409123456
```

## Integration with Existing System

The new endpoints work alongside the existing `/generate` endpoint:

1. **Scheduling Phase**: Use `/api/slots` and `/api/book`
2. **Prep Phase**: Use existing `/generate` endpoint
3. **Chat Phase**: Use `/api/chat` for Q&A
4. **Post-Procedure**: Use `/api/post-procedure`

## Frontend Integration (Optional)

If you want to add UI for the new features:

1. **Scheduling UI**: Add slot picker to `templates/agent_workspace.html`
2. **Chat Interface**: Add chat widget with message history
3. **Post-Procedure Panel**: Add recovery instructions display

Example JavaScript for booking:

```javascript
async function bookAppointment(slot, patientData) {
  const response = await fetch('/api/book', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      slot: slot,
      patient_name: patientData.name,
      appointment_type: patientData.type,
      procedure: patientData.procedure,
      email: patientData.email,
      phone: patientData.phone
    })
  });
  
  const result = await response.json();
  if (!result.error) {
    console.log('Booked:', result.event_id);
  }
}
```

## Troubleshooting

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Service Not Working
Check console for mock mode messages. If you see `[ServiceName MOCK]`, it's working correctly without credentials.

### Database Errors
```bash
# Delete and recreate database
rm data/appointments.db
python -c "from services.storage import StorageService; s = StorageService(); s.init_db()"
```

## What's Working Now

✅ All 5 new API endpoints functional
✅ Mock mode for all services (no credentials needed)
✅ Session state management
✅ Post-procedure recovery rules
✅ Context-aware patient chat
✅ Multi-channel delivery (SMS + Email)
✅ Google Calendar integration ready
✅ Backward compatible with existing system

## What's Next (Optional)

- Add frontend UI for scheduling
- Add chat interface
- Add post-procedure display
- Configure real services (Google Calendar, Twilio, SendGrid)
- Add more test cases
- Add property-based tests for new services

---

**Ready to test!** Start with `python app.py` and try the API endpoints above.
