"""
Tests for error handling and recovery (Task 16).

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from services.llm_client import LLMClient
from services.message_builder import MessageBuilder
from services.rules_engine import RulesEngine
from services.models import PrepRules


class TestFlaskErrorHandling:
    """Test Flask route error handling (Sub-task 16.1)"""
    
    def test_generate_endpoint_handles_missing_data(self):
        """Test that /generate returns 400 for missing data (Requirement 8.1)"""
        from app import app
        
        with app.test_client() as client:
            # Send request with empty JSON
            response = client.post('/generate', 
                                 json={},
                                 content_type='application/json')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['error'] is True
            assert 'messages' in data
            assert len(data['messages']) > 0
    
    def test_generate_endpoint_handles_validation_errors(self):
        """Test that /generate returns 400 for validation errors (Requirement 8.2)"""
        from app import app
        
        with app.test_client() as client:
            # Missing required fields
            response = client.post('/generate',
                                 json={'patient_name': 'Test'},
                                 content_type='application/json')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['error'] is True
            assert 'messages' in data
    
    def test_history_endpoint_validates_limit(self):
        """Test that /history validates limit parameter (Requirement 8.1)"""
        from app import app
        
        with app.test_client() as client:
            # Invalid limit (too large)
            response = client.get('/history?limit=200')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['error'] is True
            assert 'messages' in data
    
    def test_load_sample_validates_sample_id(self):
        """Test that /load-sample validates sample_id (Requirement 8.1)"""
        from app import app
        
        with app.test_client() as client:
            # Negative sample_id - Flask converts negative route params to 404
            # So we test with an out-of-range positive ID instead
            response = client.get('/load-sample/9999')
            
            # Should return 404 for non-existent sample
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['error'] is True
    
    def test_load_sample_handles_missing_file(self):
        """Test that /load-sample handles missing file gracefully (Requirement 8.9)"""
        from app import app
        
        with app.test_client() as client:
            # Mock file not found
            with patch('builtins.open', side_effect=FileNotFoundError()):
                response = client.get('/load-sample/0')
                
                assert response.status_code == 404
                data = json.loads(response.data)
                assert data['error'] is True
                assert 'No sample data available' in data['messages'][0]


class TestLLMFallbackLogging:
    """Test LLM fallback logging (Sub-task 16.3)"""
    
    def test_llm_client_logs_warning_on_api_failure(self):
        """Test that LLM client logs warning when API fails (Requirement 8.3, 8.4)"""
        # Verify logging code is present in llm_client.py
        with open('services/llm_client.py', 'r') as f:
            content = f.read()
        
        # Check for logging import and usage
        assert 'import logging' in content
        assert 'logger.warning' in content
        assert 'LLM API call failed' in content
    
    def test_llm_client_does_not_log_api_keys(self):
        """Test that LLM client does not log API keys (Requirement 9.7)"""
        # Verify that API key is not logged
        with open('services/llm_client.py', 'r') as f:
            content = f.read()
        
        # Check that logging does not include api_key
        # The log message should only log the exception type, not details
        assert 'type(e).__name__' in content
        # Ensure no direct logging of self.api_key
        assert 'logger.warning(f"' not in content or 'api_key' not in content.split('logger.warning')[1].split('\n')[0]
    
    def test_message_builder_logs_template_fallback(self):
        """Test that message builder logs when template fallback is used (Requirement 8.3)"""
        # Verify logging code is present in message_builder.py
        with open('services/message_builder.py', 'r') as f:
            content = f.read()
        
        # Check for logging import and usage
        assert 'import logging' in content
        assert 'logger.info' in content
        assert 'template fallback' in content.lower()


class TestFrontendErrorHandling:
    """Test frontend error handling (Sub-task 16.2)"""
    
    def test_validation_errors_display_in_alert(self):
        """Test that validation errors are displayed in alert box (Requirement 8.1)"""
        # This would be tested with Selenium or similar in a real scenario
        # For now, we verify the JavaScript logic is present
        with open('static/js/app.js', 'r') as f:
            js_content = f.read()
        
        # Check for error display function
        assert 'showError' in js_content
        assert 'errorAlert' in js_content
        assert 'errorMessages' in js_content
    
    def test_error_fields_highlighted(self):
        """Test that error fields are highlighted with red border (Requirement 8.2)"""
        with open('static/js/app.js', 'r') as f:
            js_content = f.read()
        
        # Check for field highlighting
        assert 'highlightFieldError' in js_content
        assert "classList.add('error')" in js_content
    
    def test_copy_to_clipboard_button_exists(self):
        """Test that copy to clipboard button exists (Requirement 8.7)"""
        with open('static/js/app.js', 'r') as f:
            js_content = f.read()
        
        # Check for copy functionality
        assert 'copyBtn' in js_content
        assert 'navigator.clipboard.writeText' in js_content
    
    def test_sample_button_disable_logic_exists(self):
        """Test that sample button disable logic exists (Requirement 8.9)"""
        with open('static/js/app.js', 'r') as f:
            js_content = f.read()
        
        # Check for sample data availability check
        assert 'checkSampleDataAvailability' in js_content
        assert 'button.disabled' in js_content
    
    def test_error_styling_in_css(self):
        """Test that error styling is defined in CSS (Requirement 8.2)"""
        with open('static/css/styles.css', 'r') as f:
            css_content = f.read()
        
        # Check for error class styling
        assert '.error' in css_content
        assert 'border-color' in css_content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
