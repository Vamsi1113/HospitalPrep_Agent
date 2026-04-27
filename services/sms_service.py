"""
services/sms_service.py

SMS integration supporting both Twilio and Fast2SMS.
Falls back to console logging when credentials not configured.
"""

import os
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SMSService:
    
    def __init__(self):
        # Twilio configuration
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_from_phone = os.getenv("TWILIO_PHONE_NUMBER", "")
        
        # Fast2SMS configuration
        self.fast2sms_api_key = os.getenv("FAST2SMS_API_KEY", "")
        
        # Determine which service to use (Fast2SMS takes priority if configured)
        self.use_fast2sms = bool(self.fast2sms_api_key)
        self.use_twilio = bool(self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_phone) and not self.use_fast2sms
        self.use_real_sms = self.use_fast2sms or self.use_twilio
        
        self._twilio_client = None
        
        if self.use_twilio:
            self._init_twilio()
        
        logger.info(f"SMSService initialized (fast2sms={self.use_fast2sms}, twilio={self.use_twilio})")
    
    def _init_twilio(self):
        """Initialize Twilio client."""
        try:
            from twilio.rest import Client
            self._twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
            logger.info("Twilio initialized successfully")
        except Exception as e:
            logger.warning(f"Twilio init failed: {e}. Using mock.")
            self.use_twilio = False
            self.use_real_sms = False
    
    def send_sms(self, to_phone: str, message: str) -> dict:
        """
        Send SMS message. Routes to Fast2SMS or Twilio based on configuration,
        otherwise logs to console.
        
        Args:
            to_phone: Recipient phone number (E.164 format for Twilio: +1234567890, 10-digit for Fast2SMS)
            message: Message text (max 1600 chars)
        
        Returns:
            dict with status, message_id, and timestamp
        """
        if self.use_fast2sms:
            return self._send_fast2sms(to_phone, message)
        elif self.use_twilio:
            return self._send_twilio_sms(to_phone, message)
        return self._send_mock_sms(to_phone, message)
    
    def _send_fast2sms(self, to_phone: str, message: str) -> dict:
        """Send SMS via Fast2SMS API."""
        try:
            import requests
            
            # Fast2SMS expects 10-digit Indian phone numbers without country code
            phone_clean = to_phone.replace("+91", "").replace("+", "").replace("-", "").replace(" ", "")
            
            url = "https://www.fast2sms.com/dev/bulkV2"
            payload = {
                "route": "q",
                "message": message,
                "language": "english",
                "flash": 0,
                "numbers": phone_clean
            }
            headers = {
                "authorization": self.fast2sms_api_key,
                "Content-Type": "application/x-www-form-urlencoded",
                "Cache-Control": "no-cache"
            }
            
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            result = response.json()
            
            if result.get("return") == True:
                return {
                    "success": True,
                    "message_id": result.get("request_id", "unknown"),
                    "status": "sent",
                    "timestamp": datetime.now().isoformat(),
                    "provider": "fast2sms"
                }
            else:
                logger.error(f"Fast2SMS send failed: {result.get('message')}")
                return {
                    "success": False,
                    "error": result.get("message", "Unknown error"),
                    "timestamp": datetime.now().isoformat(),
                    "provider": "fast2sms"
                }
        except Exception as e:
            logger.error(f"Fast2SMS send failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "provider": "fast2sms"
            }
    
    def _send_twilio_sms(self, to_phone: str, message: str) -> dict:
        """Send SMS via Twilio API."""
        try:
            # Twilio requires E.164 format (+1234567890)
            phone_clean = to_phone.strip().replace(" ", "").replace("-", "")
            if not phone_clean.startswith("+"):
                # Default to India (+91) if 10 digits and no prefix, 
                # or just add + if it looks like a country code is there but no +
                if len(phone_clean) == 10:
                    phone_clean = "+91" + phone_clean
                else:
                    phone_clean = "+" + phone_clean
            
            result = self._twilio_client.messages.create(
                body=message,
                from_=self.twilio_from_phone,
                to=phone_clean
            )
            return {
                "success": True,
                "message_id": result.sid,
                "status": result.status,
                "timestamp": datetime.now().isoformat(),
                "provider": "twilio"
            }
        except Exception as e:
            logger.error(f"Twilio send failed: {e}")
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
