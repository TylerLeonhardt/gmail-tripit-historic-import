"""Tests for flight parser"""
import pytest
from flight_processor.parsers.flight_parser import FlightParser


class TestFlightParser:
    """Test FlightParser"""
    
    def setup_method(self):
        """Setup parser for each test"""
        self.parser = FlightParser()
    
    def test_schema_org_json_ld(self):
        """Test parsing Schema.org JSON-LD"""
        html = '''
        <script type="application/ld+json">
        {
            "@type": "FlightReservation",
            "reservationNumber": "ABC123",
            "reservationFor": {
                "@type": "Flight",
                "flightNumber": "UA456",
                "departureAirport": {"@type": "Airport", "iataCode": "SFO"},
                "arrivalAirport": {"@type": "Airport", "iataCode": "JFK"},
                "departureTime": "2024-10-15T10:00:00",
                "arrivalTime": "2024-10-15T18:00:00"
            }
        }
        </script>
        '''
        
        data = self.parser.parse_schema_org(html)
        
        assert data is not None
        assert data['booking_reference'] == 'ABC123'
        assert data['flight_number'] == 'UA456'
        assert data['departure_airport'] == 'SFO'
        assert data['arrival_airport'] == 'JFK'
    
    def test_html_table_parsing(self):
        """Test parsing HTML tables"""
        html = '''
        <table>
            <tr><td>Booking Reference</td><td>ABC123</td></tr>
            <tr><td>Flight Number</td><td>UA456</td></tr>
            <tr><td>Departure Airport</td><td>San Francisco (SFO)</td></tr>
            <tr><td>Arrival Airport</td><td>New York (JFK)</td></tr>
        </table>
        '''
        
        data = self.parser.parse_html_table(html)
        
        assert data is not None
        assert data['booking_reference'] == 'ABC123'
        assert data['flight_number'] == 'UA456'
        assert data['departure_airport'] == 'SFO'
        assert data['arrival_airport'] == 'JFK'
    
    def test_regex_extraction(self):
        """Test regex-based extraction"""
        text = '''
        Your flight confirmation
        Confirmation Number: ABC123
        Flight: UA456
        Route: SFO to JFK
        Date: October 15, 2024
        '''
        
        data = self.parser.extract_flight_info_regex(text)
        
        assert data is not None
        assert data['booking_reference'] == 'ABC123'
        assert data['flight_number'] == 'UA456'
        assert data['departure_airport'] == 'SFO'
        assert data['arrival_airport'] == 'JFK'
    
    def test_multi_strategy_fallback(self):
        """Test that parser tries multiple strategies"""
        # Only regex will work for this simple text
        email_data = {
            'html_content': '',
            'text_content': 'Confirmation: ABC123, Flight UA456, SFO to JFK'
        }
        
        data = self.parser.parse(email_data)
        
        assert data is not None
        assert 'booking_reference' in data or 'flight_number' in data
    
    def test_no_data_returns_none(self):
        """Test that parser returns None when no data found"""
        email_data = {
            'html_content': '<p>No flight information here</p>',
            'text_content': 'Just some random text'
        }
        
        data = self.parser.parse(email_data)
        assert data is None
