"""Tests for AI parser (optional)"""
import pytest
from unittest.mock import Mock, patch

# Skip tests if anthropic is not installed
try:
    from flight_processor.parsers.ai_parser import AIParser
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@pytest.mark.skipif(not ANTHROPIC_AVAILABLE, reason="anthropic library not installed")
class TestAIParser:
    """Test AIParser (requires anthropic library)"""
    
    def test_init_requires_api_key(self):
        """Test that API key is required"""
        with pytest.raises(ValueError, match="API key is required"):
            AIParser(api_key=None)
    
    @patch('flight_processor.parsers.ai_parser._get_anthropic')
    def test_init_with_valid_key(self, mock_get_anthropic):
        """Test initialization with valid API key"""
        mock_anthropic = Mock()
        mock_get_anthropic.return_value = mock_anthropic
        
        parser = AIParser(api_key="test-key")
        assert parser.api_key == "test-key"
        assert parser.model == "claude-3-5-sonnet-20241022"
    
    @patch('flight_processor.parsers.ai_parser._get_anthropic')
    def test_parse_with_valid_response(self, mock_get_anthropic):
        """Test parsing with valid Claude response"""
        mock_anthropic = Mock()
        mock_client = Mock()
        mock_message = Mock()
        mock_content = Mock()
        mock_content.text = '{"booking_reference": "ABC123", "flight_number": "UA456"}'
        mock_message.content = [mock_content]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client
        mock_get_anthropic.return_value = mock_anthropic
        
        parser = AIParser(api_key="test-key")
        email_data = {
            'subject': 'Flight Confirmation',
            'text_content': 'Your confirmation ABC123 for flight UA456'
        }
        
        result = parser.parse(email_data)
        
        assert result is not None
        assert result['booking_reference'] == 'ABC123'
        assert result['flight_number'] == 'UA456'
    
    @patch('flight_processor.parsers.ai_parser._get_anthropic')
    def test_parse_with_invalid_json(self, mock_get_anthropic):
        """Test parsing with invalid JSON response"""
        mock_anthropic = Mock()
        mock_client = Mock()
        mock_message = Mock()
        mock_content = Mock()
        mock_content.text = 'Not valid JSON'
        mock_message.content = [mock_content]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client
        mock_get_anthropic.return_value = mock_anthropic
        
        parser = AIParser(api_key="test-key")
        email_data = {
            'subject': 'Flight Confirmation',
            'text_content': 'Some text'
        }
        
        result = parser.parse(email_data)
        assert result is None
    
    @patch('flight_processor.parsers.ai_parser._get_anthropic')
    def test_parse_with_empty_content(self, mock_get_anthropic):
        """Test parsing with no content"""
        mock_anthropic = Mock()
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_get_anthropic.return_value = mock_anthropic
        
        parser = AIParser(api_key="test-key")
        email_data = {
            'subject': '',
            'text_content': '',
            'html_content': ''
        }
        
        result = parser.parse(email_data)
        assert result is None


def test_flight_parser_with_ai_disabled():
    """Test FlightParser when AI is not enabled"""
    from flight_processor.parsers.flight_parser import FlightParser
    
    parser = FlightParser(use_ai=False)
    assert parser.use_ai is False
    assert parser.ai_parser is None


@patch('flight_processor.parsers.ai_parser._get_anthropic')
def test_flight_parser_with_ai_enabled(mock_get_anthropic):
    """Test FlightParser with AI enabled"""
    from flight_processor.parsers.flight_parser import FlightParser
    
    mock_anthropic = Mock()
    mock_client = Mock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_get_anthropic.return_value = mock_anthropic
    
    parser = FlightParser(use_ai=True, ai_api_key="test-key")
    
    if ANTHROPIC_AVAILABLE:
        assert parser.use_ai is True
        assert parser.ai_parser is not None
    else:
        # If anthropic not available, should gracefully disable
        assert parser.use_ai is False


def test_flight_parser_ai_requires_api_key():
    """Test that AI parsing requires API key"""
    from flight_processor.parsers.flight_parser import FlightParser
    
    parser = FlightParser(use_ai=True, ai_api_key=None)
    
    # Should gracefully disable if no API key
    assert parser.use_ai is False
    assert parser.ai_parser is None
