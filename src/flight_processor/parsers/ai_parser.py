"""AI-powered flight email parser using Claude API"""
import json
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Lazy import to avoid errors when anthropic is not installed
_anthropic = None


def _get_anthropic():
    """Lazy load anthropic library"""
    global _anthropic
    if _anthropic is None:
        try:
            import anthropic
            _anthropic = anthropic
        except ImportError:
            logger.warning(
                "anthropic library not installed. Install with: pip install anthropic"
            )
            _anthropic = False
    return _anthropic if _anthropic is not False else None


class AIParser:
    """AI-powered parser using Claude API"""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize AI parser
        
        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.api_key = api_key
        self.model = model
        self.client = None
        
        if not api_key:
            raise ValueError("Anthropic API key is required for AI parsing")
        
        anthropic = _get_anthropic()
        if anthropic is None:
            raise ImportError("anthropic library not installed")
        
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def parse(self, email_data: Dict) -> Optional[Dict]:
        """
        Parse flight details using Claude AI
        
        Args:
            email_data: Dict with html_content, text_content, subject
        
        Returns:
            Dict with extracted flight details or None
        """
        if not self.client:
            logger.error("AI parser not properly initialized")
            return None
        
        # Prepare email content
        subject = email_data.get('subject', '')
        html_content = email_data.get('html_content', '')
        text_content = email_data.get('text_content', '')
        
        # Use text content if available, otherwise extract from HTML
        content = text_content
        if not content and html_content:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'lxml')
            content = soup.get_text()
        
        if not content:
            logger.warning("No content to parse")
            return None
        
        # Truncate content if too long (Claude has token limits)
        max_content_length = 10000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "...[truncated]"
        
        prompt = self._build_prompt(subject, content)
        
        try:
            logger.info("Sending request to Claude AI for flight parsing")
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract response
            response_text = message.content[0].text
            logger.debug(f"Claude response: {response_text}")
            
            # Parse JSON response
            data = json.loads(response_text)
            
            # Validate response has at least some data
            if data and isinstance(data, dict) and len(data) > 0:
                logger.info("Successfully parsed using Claude AI")
                return data
            else:
                logger.warning("Claude returned empty or invalid data")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"AI parsing failed: {e}")
            return None
    
    def _build_prompt(self, subject: str, content: str) -> str:
        """Build prompt for Claude"""
        return f"""You are an expert at extracting flight confirmation details from emails.

Email Subject: {subject}

Email Content:
{content}

Please extract the following flight information and return it as a JSON object. Only include fields where you found clear information. Return ONLY the JSON object, no other text:

{{
  "booking_reference": "the confirmation/PNR code (usually 5-6 alphanumeric characters)",
  "flight_number": "the flight number (e.g., UA123, DL456)",
  "departure_airport": "departure airport IATA code (3 letters, e.g., SFO)",
  "arrival_airport": "arrival airport IATA code (3 letters, e.g., JFK)",
  "departure_time": "departure date/time if available",
  "arrival_time": "arrival date/time if available",
  "passenger_name": "passenger name if available",
  "airline": "airline name if clear"
}}

Important:
- Return ONLY valid JSON, nothing else
- Use null for any field you cannot find
- Be conservative - only include data you're confident about
- Airport codes should be exactly 3 uppercase letters
- Flight numbers should match pattern like "UA123" or "DL456"
- Booking references are typically 5-6 characters"""
