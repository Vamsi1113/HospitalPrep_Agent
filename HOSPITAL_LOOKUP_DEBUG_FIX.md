# Hospital Lookup Debug Fix

## Problem Identified

The hospital lookup was still using mock data despite all services being configured with `mock_mode=False`. The root cause was in the `/api/analyze` endpoint logic.

## Root Causes Found

### 1. Specialty Keyword Detection Issue
The specialty detection logic in `/api/analyze` was too restrictive:

**Before:**
```python
if "cardio" in procedure or "heart" in chief_complaint:
    specialty_keyword = "cardiology"
```

**Problem:** Sample case "Cardiac evaluation" contains "cardiac" not "cardio", so it failed to match.

**After:**
```python
if "cardio" in procedure or "cardiac" in procedure or "heart" in chief_complaint or "chest" in chief_complaint:
    specialty_keyword = "cardiology"
```

### 2. Missing Debug Logging
There was no visibility into which code path was being taken (real API vs agent workflow fallback).

## Changes Made

### 1. Enhanced Specialty Detection (`app.py` line ~840)
Added more keyword variations:
- Cardiology: Added "cardiac" check
- Radiology: Added "scan" check  
- Surgery: Added "surgical" check

### 2. Added Comprehensive Debug Logging (`app.py` line ~825-860)
```python
# DEBUG: Log location data
app.logger.info(f"[DEBUG /api/analyze] lat={lat}, lng={lng}, location={location}")

# DEBUG: Log procedure and chief complaint
app.logger.info(f"[DEBUG /api/analyze] procedure='{procedure}', chief_complaint='{chief_complaint}'")

# DEBUG: Log specialty determination
app.logger.info(f"[DEBUG /api/analyze] specialty='{specialty}', specialty_keyword='{specialty_keyword}'")

# Log which path is taken
if location and specialty_keyword:
    app.logger.info("[DEBUG /api/analyze] Taking REAL API path (Geoapify)")
else:
    app.logger.info("[DEBUG /api/analyze] Taking AGENT WORKFLOW path (fallback)")
    app.logger.info(f"[DEBUG /api/analyze] Reason: location={location is not None}, specialty_keyword={specialty_keyword is not None}")
```

## How to Test

### 1. Restart Your Flask Server
```bash
python app.py
```

### 2. Watch the Logs
The server will now show detailed debug output:
```
[DEBUG /api/analyze] lat=40.7128, lng=-74.006, location=(40.7128, -74.006)
[DEBUG /api/analyze] procedure='cardiac evaluation', chief_complaint='chest feels heavy'
[DEBUG /api/analyze] specialty='Cardiology', specialty_keyword='cardiology'
[DEBUG /api/analyze] Taking REAL API path (Geoapify)
[GEOAPIFY API] Searching hospitals near (40.7128, -74.006) radius=10000m
[GEOAPIFY API] Calling Geoapify Places API with categories=healthcare.hospital
[GEOAPIFY API] Received 15 results from Geoapify
[GEOAPIFY API] Successfully ranked 15 real hospitals
```

### 3. Test Cases to Try

#### Test Case 1: Cardiac Evaluation (Should use Geoapify)
1. Load Sample Case 0 ("Chest Pain Case")
2. Click "Analyze Symptoms"
3. Check logs for `[GEOAPIFY API]` messages
4. Verify real hospitals appear (not mock data)

#### Test Case 2: MRI Imaging (Should use Geoapify)
1. Load Sample Case 4 ("MRI with Contrast")
2. Click "Analyze Symptoms"
3. Check logs for `[GEOAPIFY API]` messages
4. Verify real hospitals appear

#### Test Case 3: Surgery (Should use Geoapify)
1. Load Sample Case 1 ("Pre-Op Surgery Case")
2. Click "Analyze Symptoms"
3. Check logs for `[GEOAPIFY API]` messages
4. Verify real hospitals appear

### 4. What to Look For

**SUCCESS indicators:**
- ✅ Logs show `[DEBUG /api/analyze] Taking REAL API path (Geoapify)`
- ✅ Logs show `[GEOAPIFY API] Searching hospitals near...`
- ✅ Logs show `[GEOAPIFY API] Received X results from Geoapify`
- ✅ Hospital names are real (from OpenStreetMap)
- ✅ Addresses are real locations near your coordinates

**FAILURE indicators:**
- ❌ Logs show `[DEBUG /api/analyze] Taking AGENT WORKFLOW path (fallback)`
- ❌ No `[GEOAPIFY API]` messages appear
- ❌ Hospital names are "St. Jude Premier Health", "Metropolitan Medical Center" (mock data)

## Expected Behavior Now

### When Location + Specialty Detected
1. Frontend captures user location via browser geolocation
2. Backend receives `lat`, `lng`, and `procedure`
3. Specialty keyword is detected from procedure
4. Real Geoapify API is called
5. Real hospitals from OpenStreetMap are returned
6. Doctors are generated for each hospital

### When Location Missing or Specialty Unknown
1. Falls back to agent workflow
2. Uses `hospital_suggestion_node` (which also uses `mock_mode=False`)
3. Returns mock data as fallback

## Verification Checklist

- [ ] Server restarts without errors
- [ ] Startup logs show `HOSPITAL MODE: REAL (Geoapify)`
- [ ] Test Case 0 (Cardiac) shows `[GEOAPIFY API]` logs
- [ ] Test Case 4 (MRI) shows `[GEOAPIFY API]` logs
- [ ] Real hospital names appear (not mock names)
- [ ] Real addresses appear
- [ ] Distance calculations work
- [ ] Doctors are generated for each hospital

## If Still Seeing Mock Data

### Check 1: Geoapify API Key
```bash
# In your .env file, verify:
GEOAPIFY_API_KEY=d866449d920e404fb4895f53d8f30a1f
```

### Check 2: Location Permission
- Browser must allow location access
- Check browser console for geolocation errors
- If denied, you'll see: `📍 Location access needed for nearby hospitals`

### Check 3: Procedure Keywords
If using a custom procedure, ensure it contains one of these keywords:
- Cardiology: "cardio", "cardiac", "heart", "chest"
- Radiology: "mri", "ct", "imaging", "scan"
- Surgery: "surgery", "surgical"
- Gastroenterology: "colon", "endoscopy"

### Check 4: API Rate Limits
Geoapify free tier: ~3,000 requests/day
- If exceeded, will fall back to mock data
- Check logs for "Request error" or "429" status

## Next Steps

1. **Test the fix** - Run the test cases above
2. **Share logs** - If still seeing issues, share the `[DEBUG /api/analyze]` logs
3. **Verify other services** - Once hospital lookup works, test SMS and Email

## Summary

The hospital lookup should now work correctly for all sample cases that include:
- User location (captured by browser)
- A procedure with recognizable specialty keywords

The debug logging will make it immediately clear which path is being taken and why.
