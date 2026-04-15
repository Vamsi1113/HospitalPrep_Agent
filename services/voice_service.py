"""
Voice Input Service

Provides voice-to-text transcription using speech recognition library.
Supports mock mode for testing without audio files.
"""

import os
import logging
from typing import Optional, Dict, Any
import io

logger = logging.getLogger(__name__)


class VoiceService:
    """Service for transcribing audio to text using speech recognition."""
    
    def __init__(self, mock_mode: bool = True):
        """
        Initialize Voice Service.
        
        Args:
            mock_mode: If True, return mock transcriptions without calling API
        """
        self.mock_mode = mock_mode
        self.recognizer = None
        
        if not mock_mode:
            try:
                import speech_recognition as sr
                self.recognizer = sr.Recognizer()
                logger.info("VoiceService initialized with speech_recognition")
            except ImportError:
                logger.warning("speech_recognition library not installed, using mock mode")
                self.mock_mode = True
    
    def transcribe_audio(self, audio_file) -> Dict[str, Any]:
        """
        Transcribe audio file to text.
        
        Args:
            audio_file: Audio file object (WAV format)
        
        Returns:
            Dict with 'error', 'text', 'confidence', 'language' fields
        """
        if self.mock_mode:
            return self._mock_transcribe(audio_file)
        
        try:
            import speech_recognition as sr
            
            # Read audio file
            audio_data = audio_file.read()
            audio_file_like = io.BytesIO(audio_data)
            
            # Convert to AudioFile
            with sr.AudioFile(audio_file_like) as source:
                audio = self.recognizer.record(source)
            
            # Transcribe using Google Speech Recognition (free)
            text = self.recognizer.recognize_google(audio)
            
            logger.info(f"Transcription successful: {len(text)} characters")
            
            return {
                "error": False,
                "text": text,
                "confidence": 0.9,  # Google API doesn't return confidence
                "language": "en-US"
            }
            
        except sr.UnknownValueError:
            logger.warning("Speech recognition could not understand audio")
            return {
                "error": True,
                "text": "",
                "message": "Could not understand audio. Please try again."
            }
        
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return {
                "error": True,
                "text": "",
                "message": "Speech recognition service is currently unavailable."
            }
        
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {
                "error": True,
                "text": "",
                "message": f"Transcription failed: {str(e)}"
            }
    
    def _mock_transcribe(self, audio_file) -> Dict[str, Any]:
        """
        Return mock transcription for testing.
        
        Args:
            audio_file: Audio file object (ignored in mock mode)
        
        Returns:
            Mock transcription result
        """
        logger.info("[MOCK] Transcribing audio file")
        
        # Return realistic mock transcription
        mock_text = (
            "I've been having chest tightness and shortness of breath for the past two days. "
            "It gets worse when I exert myself. I'm also feeling a bit dizzy."
        )
        
        return {
            "error": False,
            "text": mock_text,
            "confidence": 0.95,
            "language": "en-US"
        }
    
    def is_available(self) -> bool:
        """
        Check if voice service is available.
        
        Returns:
            True if service is available (mock or real)
        """
        return True  # Always available (mock or real)
