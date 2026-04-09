"""
services/sms_service.py

Twilio SMS integration for appointment reminders and notifications.
Falls back to console logging when credentials not configured.
Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in .env to enable.
"""

import os
from datetime import datetime
from typing import Optional


class SMSService:
    
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.from_phone = os.getenv("TWILIO_PHONE_NUMBER", "")
        self.use_real_sms = bool(self.account_sid and self.auth_token and self.from_phone)
        self._client = None
        
        if self.use_real_sms:
            self._init_twilio()
    
    def _init_twilio(self):
        """Initialize Twilio client."""
        try:
            from twilio.rest import Client
            self._client = Client(self.account_sid, self.auth_token)
        except Exception as e:
            print(f"[SMSService] Twilio init failed: {e}. Using mock.")
            self.use_real_sms = False
    
    def send_sms(self, to_phone: str, message: str) -> dict:
        """
        Send SMS message. Uses real Twilio if configured,
        otherwise logs to console.
        
        Args:
            to_phone: Recipient phone number (E.164 format: +1234567890)
            message: Message text (max 1600 chars)
        
        Returns:
            dict with status, message_id, and timestamp
        """
        if self.use_real_sms:
            return self._send_real_sms(to_phone, message)
        return self._send_mock_sms(to_phone, message)
    
    def _send_real_sms(self, to_phone: str, message: str) -> dict:
        """Send SMS via Twilio API."""
        try:
            result = self._client.messages.create(
                body=message,
                from_=self.from_phone,
                to=to_phone
            )
            return {
                "success": True,
                "message_id": result.sid,
                "status": result.status,
                "timestamp": datetime.now().isoformat(),
                "provider": "twilio"
            }
        except Exception as e:
            print(f"[SMSService] Twilio send failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "provider": "twilio"
            }
    
    def _send_mock_sms(self, to_phone: str, message: str) -> dict:
        """Mock SMS send for demo mode."""
        mock_id = f"MOCK_SMS_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        print(f"\n[SMSService MOCK] SMS sent to {to_phone}")
        print(f"Message ID: {mock_id}")
        print(f"Message: {message[:100]}...")
        print()
        
        return {
            "success": True,
            "message_id": mock_id,
            "status": "delivered",
            "timestamp": datetime.now().isoformat(),
            "provider": "mock"
        }
    
    def send_appointment_reminder(self, to_phone: str, 
                                 appointment_datetime: str,
                                 location: str,
                                 prep_instructions: str) -> dict:
        """
        Send appointment reminder SMS with prep instructions.
        
        Args:
            to_phone: Patient phone number
            appointment_datetime: Formatted appointment date/time
            location: Clinic location
            prep_instructions: Brief prep instructions
        
        Returns:
            dict with send status
        """
        message = f"Appointment Reminder\n\n"
        message += f"Date/Time: {appointment_datetime}\n"
        message += f"Location: {location}\n\n"
        message += f"Preparation:\n{prep_instructions}\n\n"
        message += f"Reply HELP for assistance or call clinic to reschedule."
        
        return self.send_sms(to_phone, message)
    
    def send_booking_confirmation(self, to_phone: str,
                                 appointment_datetime: str,
                                 doctor: str,
                                 location: str) -> dict:
        """
        Send booking confirmation SMS.
        
        Args:
            to_phone: Patient phone number
            appointment_datetime: Formatted appointment date/time
            doctor: Doctor name
            location: Clinic location
        
        Returns:
            dict with send status
        """
        message = f"Appointment Confirmed!\n\n"
        message += f"Date/Time: {appointment_datetime}\n"
        message += f"Doctor: {doctor}\n"
        message += f"Location: {location}\n\n"
        message += f"You will receive prep instructions 24 hours before your appointment."
        
        return self.send_sms(to_phone, message)
    
    def send_cancellation_notice(self, to_phone: str,
                                appointment_datetime: str) -> dict:
        """
        Send cancellation notice SMS.
        
        Args:
            to_phone: Patient phone number
            appointment_datetime: Cancelled appointment date/time
        
        Returns:
            dict with send status
        """
        message = f"Appointment Cancelled\n\n"
        message += f"Your appointment on {appointment_datetime} has been cancelled.\n\n"
        message += f"Call clinic to reschedule: [CLINIC_PHONE]"
        
        return self.send_sms(to_phone, message)
