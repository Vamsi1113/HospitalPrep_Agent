"""
services/email_service.py

Email integration supporting both Gmail API and SendGrid.
Falls back to console logging when credentials not configured.
"""

import os
from datetime import datetime
from typing import Optional, List
import base64
import logging

logger = logging.getLogger(__name__)


class EmailService:
    
    def __init__(self):
        # Gmail API configuration
        self.gmail_sender = os.getenv("GMAIL_SENDER_ADDRESS", "")
        self.gmail_creds_path = os.getenv("GMAIL_OAUTH_CREDENTIALS_JSON", "")
        
        # SendGrid configuration
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "")
        self.sendgrid_from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@clinic.example.com")
        
        # Determine which service to use
        self.use_gmail = bool(self.gmail_sender and self.gmail_creds_path)
        self.use_sendgrid = bool(self.sendgrid_api_key) and not self.use_gmail
        self.use_real_email = self.use_gmail or self.use_sendgrid
        
        self._gmail_service = None
        self._sendgrid_client = None
        
        if self.use_gmail:
            self._init_gmail()
        elif self.use_sendgrid:
            self._init_sendgrid()
        
        logger.info(f"EmailService initialized (gmail={self.use_gmail}, sendgrid={self.use_sendgrid})")
    
    def _init_gmail(self):
        """Initialize Gmail API client."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            SCOPES = ['https://www.googleapis.com/auth/gmail.send']
            
            credentials = service_account.Credentials.from_service_account_file(
                self.gmail_creds_path,
                scopes=SCOPES
            )
            
            self._gmail_service = build('gmail', 'v1', credentials=credentials)
            logger.info("Gmail API initialized successfully")
            
        except Exception as e:
            logger.warning(f"Gmail API init failed: {e}. Using mock.")
            self.use_gmail = False
            self.use_real_email = False
    
    def _init_sendgrid(self):
        """Initialize SendGrid client."""
        try:
            from sendgrid import SendGridAPIClient
            self._sendgrid_client = SendGridAPIClient(self.sendgrid_api_key)
            logger.info("SendGrid initialized successfully")
        except Exception as e:
            logger.warning(f"SendGrid init failed: {e}. Using mock.")
            self.use_sendgrid = False
            self.use_real_email = False
    
    def send_email(self, to_email: str, subject: str, 
                  html_content: str, plain_content: str = "") -> dict:
        """
        Send email. Routes to Gmail or SendGrid based on configuration,
        otherwise logs to console.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML email body
            plain_content: Plain text fallback (optional)
        
        Returns:
            dict with status, message_id, and timestamp
        """
        if self.use_gmail:
            return self._send_gmail_email(to_email, subject, html_content, plain_content)
        elif self.use_sendgrid:
            return self._send_sendgrid_email(to_email, subject, html_content, plain_content)
        return self._send_mock_email(to_email, subject, html_content)
    
    def _send_gmail_email(self, to_email: str, subject: str,
                         html_content: str, plain_content: str) -> dict:
        """Send email via Gmail API."""
        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            message = MIMEMultipart('alternative')
            message['To'] = to_email
            message['From'] = self.gmail_sender
            message['Subject'] = subject
            
            if plain_content:
                message.attach(MIMEText(plain_content, 'plain'))
            message.attach(MIMEText(html_content, 'html'))
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            result = self._gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return {
                "success": True,
                "message_id": result.get('id', 'unknown'),
                "status_code": 200,
                "timestamp": datetime.now().isoformat(),
                "provider": "gmail"
            }
        except Exception as e:
            logger.error(f"Gmail send failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "provider": "gmail"
            }
    
    def _send_sendgrid_email(self, to_email: str, subject: str,
                            html_content: str, plain_content: str) -> dict:
        """Send email via SendGrid API."""
        try:
            from sendgrid.helpers.mail import Mail, Content
            
            message = Mail(
                from_email=self.sendgrid_from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            if plain_content:
                message.add_content(Content("text/plain", plain_content))
            
            response = self._sendgrid_client.send(message)
            
            return {
                "success": True,
                "status_code": response.status_code,
                "message_id": response.headers.get("X-Message-Id", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "provider": "sendgrid"
            }
        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "provider": "sendgrid"
            }
    
    def _send_mock_email(self, to_email: str, subject: str, html_content: str) -> dict:
        """Mock email send for demo mode."""
        mock_id = f"MOCK_EMAIL_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        print(f"\n[EmailService MOCK] Email sent to {to_email}")
        print(f"Subject: {subject}")
        print(f"Message ID: {mock_id}")
        print(f"Content preview: {html_content[:150]}...")
        print()
        
        return {
            "success": True,
            "message_id": mock_id,
            "status_code": 200,
            "timestamp": datetime.now().isoformat(),
            "provider": "mock"
        }
    
    def send_prep_instructions(self, to_email: str, patient_name: str,
                              appointment_datetime: str, prep_message: str) -> dict:
        """
        Send appointment prep instructions email.
        
        Args:
            to_email: Patient email address
            patient_name: Patient name
            appointment_datetime: Formatted appointment date/time
            prep_message: Full prep instructions
        
        Returns:
            dict with send status
        """
        subject = f"Appointment Preparation Instructions - {appointment_datetime}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #2c5aa0;">Appointment Preparation Guide</h2>
            <p>Dear {patient_name},</p>
            <p>Please review the following preparation instructions for your upcoming appointment:</p>
            <div style="background-color: #f5f5f5; padding: 20px; border-left: 4px solid #2c5aa0; margin: 20px 0;">
                <pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">{prep_message}</pre>
            </div>
            <p>If you have any questions, please contact our clinic.</p>
            <p style="color: #666; font-size: 0.9em;">This is an automated message. Please do not reply to this email.</p>
        </body>
        </html>
        """
        
        plain_content = f"Appointment Preparation Guide\n\n{prep_message}"
        
        return self.send_email(to_email, subject, html_content, plain_content)
    
    def send_booking_confirmation(self, to_email: str, patient_name: str,
                                 appointment_datetime: str, doctor: str,
                                 location: str, prep_summary: str) -> dict:
        """
        Send booking confirmation email.
        
        Args:
            to_email: Patient email address
            patient_name: Patient name
            appointment_datetime: Formatted appointment date/time
            doctor: Doctor name
            location: Clinic location
            prep_summary: Brief prep summary
        
        Returns:
            dict with send status
        """
        subject = f"Appointment Confirmed - {appointment_datetime}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #2c5aa0;">Appointment Confirmed</h2>
            <p>Dear {patient_name},</p>
            <p>Your appointment has been successfully scheduled:</p>
            <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Date/Time:</strong> {appointment_datetime}</p>
                <p><strong>Doctor:</strong> {doctor}</p>
                <p><strong>Location:</strong> {location}</p>
            </div>
            <h3 style="color: #2c5aa0;">Preparation Summary</h3>
            <p>{prep_summary}</p>
            <p>You will receive detailed preparation instructions 24 hours before your appointment.</p>
            <p>If you need to cancel or reschedule, please contact our clinic as soon as possible.</p>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def send_post_procedure_instructions(self, to_email: str, patient_name: str,
                                        procedure: str, instructions: str) -> dict:
        """
        Send post-procedure recovery instructions email.
        
        Args:
            to_email: Patient email address
            patient_name: Patient name
            procedure: Procedure name
            instructions: Recovery instructions
        
        Returns:
            dict with send status
        """
        subject = f"Post-Procedure Recovery Instructions - {procedure}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #2c5aa0;">Post-Procedure Recovery Instructions</h2>
            <p>Dear {patient_name},</p>
            <p>Thank you for visiting our clinic. Please follow these recovery instructions:</p>
            <div style="background-color: #fff3cd; padding: 20px; border-left: 4px solid #ffc107; margin: 20px 0;">
                <pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">{instructions}</pre>
            </div>
            <p style="color: #d9534f; font-weight: bold;">⚠️ If you experience any concerning symptoms, contact your doctor immediately or seek emergency care.</p>
            <p>We hope you have a smooth recovery!</p>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
