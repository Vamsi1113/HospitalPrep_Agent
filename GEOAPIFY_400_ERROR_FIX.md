# Geoapify 400 Error Fix

## Problem

Geoapify API was returning `400 Bad Request` error:
```
[GEOAPIFY API] Request error: 400 Client Error: Bad Request for url: 
https://api.geoapify.com/v2/places?...&filter=circle%3A73.883%2C18.5344%2C10000.0&...
```

## Root Cause

The radius parameter was being passed as a float (`10000.0`) instead of an integer (`10000`). Geoapify's API expects the radius in the `circle` filter to be an integer value.

## The Fix

Changed the radius conversion to explicitly cast to integer:

**Before:**
```python
# In search_hospitals method
return self.search_real_hospitals(location[0], location[1], procedure, radius_km * 1000)

# In search_real_hospitals method
params = {
    "filter": f"circle:{lng},{lat},{radius}",
    ...
}
```

**After:**
```python
# In search_hospitals method
return self.search_real_hospitals(location[0], location[1], procedure, int(radius_km * 1000))

# In search_real_hospitals method
params = {
    "filter": f"circle:{lng},{lat},{int(radius)}",
    ...
}
```

## What to Do Now

1. **Restart your server:**
   ```bash
   # Stop with Ctrl+C
   python app.py
   ```

2. **Test again with Sample Case 0:**
   - Load "Chest Pain Case"
   - Click "Analyze Symptoms"
   - Allow location access

3. **Expected logs:**
   ```
   [GEOAPIFY API] Request params: filter=circle:73.883,18.5344,10000
   [GEOAPIFY API] Calling Geoapify Places API with categories=healthcare.hospital
   [GEOAPIFY API] Received X results from Geoapify
   [GEOAPIFY API] Successfully ranked X real hospitals
   ```

## Verification

✅ **Success indicators:**
- No more `400 Bad Request` errors
- Logs show `Received X results from Geoapify`
- Real hospital names appear (from OpenStreetMap)
- Hospitals are near your location (Mumbai area based on coordinates 18.5344, 73.883)

❌ **If still failing:**
- Share the complete error message
- Check if Geoapify API key is valid
- Verify you haven't exceeded the free tier limit (3000 requests/day)

## Summary

The Geoapify API now receives properly formatted parameters with integer radius values, which should resolve the 400 error and return real hospital data.
