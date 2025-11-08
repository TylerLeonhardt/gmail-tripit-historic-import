"""Tests for flight classifier"""
import pytest
from flight_processor.parsers.classifier import FlightClassifier


class TestFlightClassifier:
    """Test FlightClassifier"""
    
    def setup_method(self):
        """Setup classifier for each test"""
        self.classifier = FlightClassifier()
    
    def test_schema_org_detection(self):
        """Test Schema.org FlightReservation detection"""
        html = '''
        <html>
        <script type="application/ld+json">
        {
            "@type": "FlightReservation",
            "reservationStatus": "Confirmed",
            "reservationNumber": "ABC123"
        }
        </script>
        </html>
        '''
        
        email_data = {
            'subject': 'Your flight confirmation',
            'from_email': 'noreply@united.com',
            'html_content': html,
            'text_content': ''
        }
        
        is_flight, score = self.classifier.classify(email_data)
        assert is_flight
        assert score >= 50
    
    def test_confirmation_subject(self):
        """Test confirmation subject pattern matching"""
        assert self.classifier.is_confirmation_subject('Flight Confirmation - UA123')
        assert self.classifier.is_confirmation_subject('Your booking is confirmed')
        assert self.classifier.is_confirmation_subject('Itinerary Confirmation')
        
        # Should reject exclusions
        assert not self.classifier.is_confirmation_subject('Flight Cancelled')
        assert not self.classifier.is_confirmation_subject('Check-in now available')
        assert not self.classifier.is_confirmation_subject('Flight Change Notification')
    
    def test_airline_domain(self):
        """Test airline domain detection"""
        assert self.classifier.is_airline_domain('noreply@united.com')
        assert self.classifier.is_airline_domain('confirmations@delta.com')
        assert self.classifier.is_airline_domain('email@aa.com')
        
        assert not self.classifier.is_airline_domain('user@gmail.com')
        assert not self.classifier.is_airline_domain('spam@example.com')
    
    def test_flight_markers(self):
        """Test flight marker detection in content"""
        text = '''
        Your booking is confirmed!
        Confirmation Number: ABC123
        Flight: UA456
        From: SFO to JFK
        Departure: October 15, 2024
        '''
        
        assert self.classifier.has_flight_markers(text)
    
    def test_combined_classification(self):
        """Test combined classification with multiple signals"""
        email_data = {
            'subject': 'Your Flight Confirmation',
            'from_email': 'noreply@united.com',
            'html_content': '<p>Confirmation: ABC123, Flight UA456, SFO to JFK</p>',
            'text_content': 'Confirmation: ABC123, Flight UA456, SFO to JFK'
        }
        
        is_flight, score = self.classifier.classify(email_data)
        assert is_flight
        assert score >= 50
    
    def test_non_flight_email(self):
        """Test that non-flight emails are rejected"""
        email_data = {
            'subject': 'Newsletter: Travel Deals',
            'from_email': 'marketing@example.com',
            'html_content': '<p>Great deals on flights!</p>',
            'text_content': 'Great deals on flights!'
        }
        
        is_flight, score = self.classifier.classify(email_data)
        assert not is_flight
        assert score < 50
