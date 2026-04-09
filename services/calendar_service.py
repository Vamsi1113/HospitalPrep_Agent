"""
services/calendar_service.py

Google Calendar integration for appointment scheduling.
Falls back to in-memory mock calendar when credentials not configured.
Set GOOGLE_CALENDAR_ID and GOOGLE_SERVICE_ACCOUNT_JSON in .env to enable.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class CalendarService:
    
    def __init__(self):
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "")
        self.service_account_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        self.use_real_calendar = bool(self.calendar_id and self.service_account_path)
        self._service = None
        
        if self.use_real_calendar:
            self._init_google_calendar()
    
    def _init_google_calendar(self):
        """Initialize Google Calendar API client."""
        try:
            from googleapiclient.discovery import build
            from google.oauth2 import service_account
            
            creds = service_account.Credentials.from_service_account_file(
                self.service_account_path,
                scopes=["https://www.googleapis.com/auth/calendar"]
            )
            self._service = build("calendar", "v3", credentials=creds)
        except Exception as e:
            print(f"[CalendarService] Google Calendar init failed: {e}. Using mock.")
            self.use_real_calendar = False
    
    def get_available_slots(self, appointment_type: str,
                            preferred_date: str = "",
                            duration_minutes: int = 30) -> List[Dict]:
        """
        Returns available time slots. Uses real calendar if configured,
        otherwise generates realistic mock slots.
        """
        if self.use_real_calendar:
            return self._get_real_slots(preferred_date, duration_minutes)
        return self._get_mock_slots(appointment_type, preferred_date, duration_minutes)
    
    def _get_real_slots(self, preferred_date: str,
                        duration_minutes: int) -> List[Dict]:
        """Query real Google Calendar for free/busy slots."""
        try:
            # Parse preferred date or default to next 7 days
            if preferred_date:
                start_dt = datetime.fromisoformat(preferred_date)
            else:
                start_dt = datetime.now() + timedelta(days=1)
            
            end_dt = start_dt + timedelta(days=7)
            
            # Get busy slots
            body = {
                "timeMin": start_dt.isoformat() + "Z",
                "timeMax": end_dt.isoformat() + "Z",
                "items": [{"id": self.calendar_id}]
            }
            result = self._service.freebusy().query(body=body).execute()
            busy_slots = result.get("calendars", {}).get(self.calendar_id, {}).get("busy", [])
            
            # Generate available slots in clinic hours (9am-5pm)
            available = []
            current = start_dt.replace(hour=9, minute=0, second=0)
            
            while current < end_dt and len(available) < 6:
                slot_end = current + timedelta(minutes=duration_minutes)
                # Check not busy
                is_busy = any(
                    datetime.fromisoformat(b["start"].rstrip("Z")) <= current < 
                    datetime.fromisoformat(b["end"].rstrip("Z"))
                    for b in busy_slots
                )
                # Clinic hours only
                if not is_busy and 9 <= current.hour < 17 and current.weekday() < 5:
                    available.append(self._format_slot(current, slot_end))
                current += timedelta(minutes=30)
            
            return available
        except Exception as e:
            print(f"[CalendarService] Real calendar query failed: {e}")
            return self._get_mock_slots("", "", duration_minutes)
    
    def _get_mock_slots(self, appointment_type: str,
                        preferred_date: str,
                        duration_minutes: int) -> List[Dict]:
        """Generate realistic mock time slots for demo mode."""
        slots = []
        base = datetime.now() + timedelta(days=1)
        base = base.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Generate 6 slots over 2 days
        slot_times = [
            (0, 9, 0), (0, 10, 30), (0, 14, 0),
            (1, 9, 30), (1, 11, 0), (1, 15, 30),
        ]
        doctors = {
            "Surgery": "Dr. Mehta (Surgery)",
            "blood_test": "Lab Technician",
            "Imaging": "Dr. Sharma (Radiology)",
            "dental_cleaning": "Dr. Singh (Dental)",
            "psychotherapy": "Dr. Verma (Psychology)",
            "Consultation": "Dr. Kapoor (General)",
            "Procedure": "Dr. Patel (Procedures)",
        }
        doctor = doctors.get(appointment_type, doctors["Consultation"])
        
        for day_offset, hour, minute in slot_times:
            start = base + timedelta(days=day_offset, hours=hour-9, minutes=minute)
            end = start + timedelta(minutes=duration_minutes)
            slots.append(self._format_slot(start, end, doctor))
        
        return slots
    
    def _format_slot(self, start: datetime, end: datetime,
                     doctor: str = "Doctor TBD") -> Dict:
        return {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "start_formatted": start.strftime("%A, %d %b %Y at %I:%M %p"),
            "end_formatted": end.strftime("%I:%M %p"),
            "doctor": doctor,
            "location": "Main Clinic, Floor 2",
            "slot_id": f"SLOT_{start.strftime('%Y%m%d%H%M')}",
        }
    
    def create_appointment_event(self, title: str, start_time: str,
                                end_time: str, description: str,
                                attendee_email: str, location: str) -> str:
        """
        Creates a Google Calendar event. Returns event ID.
        Returns mock ID if real calendar not configured.
        """
        if not self.use_real_calendar:
            mock_id = f"MOCK_EVT_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            print(f"[CalendarService MOCK] Event created: {title} → {mock_id}")
            return mock_id
        
        try:
            event = {
                "summary": title,
                "location": location,
                "description": description,
                "start": {"dateTime": start_time, "timeZone": "Asia/Kolkata"},
                "end": {"dateTime": end_time, "timeZone": "Asia/Kolkata"},
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "email", "minutes": 1440},  # 24h
                        {"method": "popup", "minutes": 60},
                    ],
                },
            }
            if attendee_email:
                event["attendees"] = [{"email": attendee_email}]
            
            result = self._service.events().insert(
                calendarId=self.calendar_id, 
                body=event,
                sendUpdates="all"
            ).execute()
            return result.get("id", "")
        except Exception as e:
            print(f"[CalendarService] Event creation failed: {e}")
            return f"ERROR_{datetime.now().strftime('%H%M%S')}"
    
    def cancel_appointment(self, event_id: str) -> bool:
        """Cancel an existing appointment."""
        if not self.use_real_calendar:
            print(f"[CalendarService MOCK] Event cancelled: {event_id}")
            return True
        try:
            self._service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            return True
        except Exception as e:
            print(f"[CalendarService] Cancel failed: {e}")
            return False
    
    def reschedule_appointment(self, event_id: str,
                             new_start: str, new_end: str) -> bool:
        """Move an existing appointment to a new time slot."""
        if not self.use_real_calendar:
            print(f"[CalendarService MOCK] Rescheduled: {event_id} → {new_start}")
            return True
        try:
            event = self._service.events().get(
                calendarId=self.calendar_id, eventId=event_id
            ).execute()
            event["start"]["dateTime"] = new_start
            event["end"]["dateTime"] = new_end
            self._service.events().update(
                calendarId=self.calendar_id, eventId=event_id, body=event
            ).execute()
            return True
        except Exception as e:
            print(f"[CalendarService] Reschedule failed: {e}")
            return False
