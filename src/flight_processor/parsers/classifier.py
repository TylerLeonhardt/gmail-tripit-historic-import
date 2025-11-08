"""Flight email classifier - determines if an email is a flight confirmation"""
import re
import logging
from bs4 import BeautifulSoup
import json

logger = logging.getLogger(__name__)


# Confirmation patterns
CONFIRMATION_PATTERNS = [
    r'(?i)(flight|booking|reservation).*confirm(ed|ation)',
    r'(?i)confirm.*flight',
    r'(?i)itinerary.*confirm',
    r'(?i)booking.*confirm'
]

# Exclusion patterns
EXCLUSION_PATTERNS = [
    r'(?i)cancel',
    r'(?i)check[\s-]*in',
    r'(?i)(change|update|modif)',
    r'(?i)reminder',
    r'(?i)expired'
]

# Known airline domains
AIRLINE_DOMAINS = [
    'united.com', 'delta.com', 'aa.com', 'americanairlines.com',
    'southwest.com', 'luv.southwest.com', 'jetblue.com',
    'alaskaair.com', 'spirit.com', 'frontier.com',
    'expedia.com', 'welcomemail.expedia.com', 'kayak.com', 'priceline.com'
]


class FlightClassifier:
    """Classifies emails as flight confirmations using multiple strategies"""
    
    def __init__(self):
        self.confirmation_patterns = [re.compile(p) for p in CONFIRMATION_PATTERNS]
        self.exclusion_patterns = [re.compile(p) for p in EXCLUSION_PATTERNS]
    
    def classify(self, email_data):
        """
        Classify if email is a flight confirmation
        
        Args:
            email_data: Dict with subject, from_email, html_content, text_content
        
        Returns:
            Tuple (is_flight_confirmation: bool, confidence_score: int)
        """
        score = 0
        reasons = []
        
        subject = email_data.get('subject', '')
        from_email = email_data.get('from_email', '')
        html_content = email_data.get('html_content', '')
        text_content = email_data.get('text_content', '')
        
        # Check for Schema.org FlightReservation (highest confidence)
        if html_content and self.has_flight_reservation_schema(html_content):
            score += 50
            reasons.append("Schema.org FlightReservation found")
            logger.debug(f"Schema.org detected in email")
        
        # Check sender domain
        if self.is_airline_domain(from_email):
            score += 20
            reasons.append(f"Airline domain: {from_email}")
            logger.debug(f"Airline domain detected: {from_email}")
        
        # Check subject line
        if self.is_confirmation_subject(subject):
            score += 20
            reasons.append("Confirmation subject pattern")
            logger.debug(f"Confirmation subject detected: {subject[:50]}")
        
        # Check content markers
        combined_content = f"{subject} {text_content}"
        if self.has_flight_markers(combined_content):
            score += 10
            reasons.append("Flight markers in content")
            logger.debug("Flight markers detected in content")
        
        is_flight = score >= 50
        
        if is_flight:
            logger.info(f"Classified as flight confirmation (score: {score}): {', '.join(reasons)}")
        else:
            logger.debug(f"Not classified as flight (score: {score})")
        
        return is_flight, score
    
    def has_flight_reservation_schema(self, html):
        """Check for Schema.org FlightReservation markup"""
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Check for JSON-LD
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    if script.string:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and data.get('@type') == 'FlightReservation':
                            status = data.get('reservationStatus', '')
                            if 'Confirmed' in status:
                                return True
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and item.get('@type') == 'FlightReservation':
                                    status = item.get('reservationStatus', '')
                                    if 'Confirmed' in status:
                                        return True
                except (json.JSONDecodeError, AttributeError):
                    continue
            
            # Check for Microdata
            reservation = soup.find('div', itemtype='http://schema.org/FlightReservation')
            if reservation:
                return True
            
        except Exception as e:
            logger.debug(f"Schema.org check failed: {e}")
        
        return False
    
    def is_confirmation_subject(self, subject):
        """Check if subject matches confirmation pattern without exclusions"""
        has_confirm = any(pattern.search(subject) for pattern in self.confirmation_patterns)
        has_exclusion = any(pattern.search(subject) for pattern in self.exclusion_patterns)
        return has_confirm and not has_exclusion
    
    def is_airline_domain(self, from_email):
        """Check if sender is from a known airline domain"""
        from_lower = from_email.lower()
        return any(domain in from_lower for domain in AIRLINE_DOMAINS)
    
    def has_flight_markers(self, text_content):
        """Check for multiple flight-related markers in content"""
        markers = {
            'confirmation_number': bool(re.search(r'\b[A-Z0-9]{6}\b', text_content)),
            'flight_number': bool(re.search(r'\b[A-Z]{2}\d{1,4}\b', text_content)),
            'airport_code': len(re.findall(r'\b[A-Z]{3}\b', text_content)) >= 2,
            'booking_ref': bool(re.search(
                r'(?i)(confirmation|booking|reservation|pnr).{0,20}([A-Z0-9]{5,6})', 
                text_content
            ))
        }
        return sum(markers.values()) >= 3
