"""Flight email parser - extracts flight details from emails"""
import re
import logging
from bs4 import BeautifulSoup
import json
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class FlightParser:
    """Multi-strategy flight email parser"""
    
    def parse(self, email_data):
        """
        Parse flight details from email using multiple strategies
        
        Args:
            email_data: Dict with html_content and text_content
        
        Returns:
            Dict with extracted flight details or None
        """
        html_content = email_data.get('html_content', '')
        text_content = email_data.get('text_content', '')
        
        # Strategy 1: Schema.org markup
        if html_content:
            try:
                data = self.parse_schema_org(html_content)
                if data:
                    logger.info("Successfully parsed using Schema.org")
                    return data
            except Exception as e:
                logger.debug(f"Schema.org parsing failed: {e}")
        
        # Strategy 2: HTML table parsing
        if html_content:
            try:
                data = self.parse_html_table(html_content)
                if data:
                    logger.info("Successfully parsed using HTML tables")
                    return data
            except Exception as e:
                logger.debug(f"HTML table parsing failed: {e}")
        
        # Strategy 3: Regex on text content
        try:
            combined_text = text_content
            if html_content:
                soup = BeautifulSoup(html_content, 'lxml')
                combined_text = soup.get_text() + " " + text_content
            
            data = self.extract_flight_info_regex(combined_text)
            if data:
                logger.info("Successfully parsed using regex")
                return data
        except Exception as e:
            logger.debug(f"Regex parsing failed: {e}")
        
        logger.warning("All parsing strategies failed")
        return None
    
    def parse_schema_org(self, html):
        """Parse Schema.org FlightReservation markup"""
        soup = BeautifulSoup(html, 'lxml')
        data = {}
        
        # Try JSON-LD first
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                if not script.string:
                    continue
                
                json_data = json.loads(script.string)
                items = [json_data] if isinstance(json_data, dict) else json_data
                
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    
                    if item.get('@type') == 'FlightReservation':
                        # Extract reservation number
                        if 'reservationNumber' in item:
                            data['booking_reference'] = item['reservationNumber']
                        
                        # Extract flight details
                        flight = item.get('reservationFor', {})
                        if flight.get('@type') == 'Flight':
                            if 'flightNumber' in flight:
                                data['flight_number'] = flight['flightNumber']
                            
                            # Departure
                            dep = flight.get('departureAirport', {})
                            if isinstance(dep, dict) and 'iataCode' in dep:
                                data['departure_airport'] = dep['iataCode']
                            
                            # Arrival
                            arr = flight.get('arrivalAirport', {})
                            if isinstance(arr, dict) and 'iataCode' in arr:
                                data['arrival_airport'] = arr['iataCode']
                            
                            # Times
                            if 'departureTime' in flight:
                                data['departure_time'] = flight['departureTime']
                            if 'arrivalTime' in flight:
                                data['arrival_time'] = flight['arrivalTime']
                        
                        if data:
                            return data
            
            except (json.JSONDecodeError, AttributeError, KeyError) as e:
                logger.debug(f"JSON-LD parsing error: {e}")
                continue
        
        # Try Microdata
        reservation = soup.find('div', itemtype='http://schema.org/FlightReservation')
        if reservation:
            res_num = reservation.find('meta', itemprop='reservationNumber')
            if res_num and res_num.get('content'):
                data['booking_reference'] = res_num['content']
            
            flight = reservation.find('div', itemtype='http://schema.org/Flight')
            if flight:
                flight_num = flight.find('meta', itemprop='flightNumber')
                if flight_num and flight_num.get('content'):
                    data['flight_number'] = flight_num['content']
                
                airports = flight.find_all('div', itemtype='http://schema.org/Airport')
                if len(airports) >= 2:
                    dep_code = airports[0].find('meta', itemprop='iataCode')
                    arr_code = airports[1].find('meta', itemprop='iataCode')
                    if dep_code and dep_code.get('content'):
                        data['departure_airport'] = dep_code['content']
                    if arr_code and arr_code.get('content'):
                        data['arrival_airport'] = arr_code['content']
        
        return data if data else None
    
    def parse_html_table(self, html):
        """Parse flight details from HTML tables"""
        soup = BeautifulSoup(html, 'lxml')
        tables = soup.find_all('table')
        
        for table in tables:
            table_text = table.get_text().lower()
            if any(keyword in table_text for keyword in ['flight', 'booking', 'departure', 'arrival']):
                data = {}
                rows = table.find_all('tr')
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text().strip().lower()
                        value = cells[1].get_text().strip()
                        
                        if ('booking' in key or 'confirmation' in key or 'pnr' in key) and len(value) >= 5:
                            data['booking_reference'] = value
                        elif 'flight' in key and 'number' in key:
                            data['flight_number'] = value
                        elif 'departure' in key:
                            if 'airport' in key or 'from' in key:
                                # Extract airport code if present
                                match = re.search(r'\b([A-Z]{3})\b', value)
                                if match:
                                    data['departure_airport'] = match.group(1)
                        elif 'arrival' in key or 'destination' in key:
                            if 'airport' in key or 'to' in key:
                                match = re.search(r'\b([A-Z]{3})\b', value)
                                if match:
                                    data['arrival_airport'] = match.group(1)
                
                if data:
                    return data
        
        return None
    
    def extract_flight_info_regex(self, text):
        """Extract flight info using regex patterns"""
        data = {}
        
        # Booking reference (look near keywords)
        booking = re.search(
            r'(?:booking|confirmation|reference|pnr)[:\s]+([A-Z0-9]{5,7})',
            text,
            re.IGNORECASE
        )
        if booking:
            data['booking_reference'] = booking.group(1).upper()
        
        # Flight number (more specific pattern)
        flight = re.search(r'\b([A-Z]{2}\s?\d{3,4})\b', text)
        if flight:
            data['flight_number'] = flight.group(1).replace(' ', '')
        
        # Airport codes (pattern: XXX to YYY or XXX - YYY or XXX→YYY)
        airports = re.search(r'\b([A-Z]{3})\s*(?:to|→|-|–)\s*([A-Z]{3})\b', text)
        if airports:
            data['departure_airport'] = airports.group(1)
            data['arrival_airport'] = airports.group(2)
        
        # Alternative: just find all 3-letter codes and take first two
        if 'departure_airport' not in data:
            codes = re.findall(r'\b([A-Z]{3})\b', text)
            # Filter out common false positives
            false_positives = {'THE', 'AND', 'FOR', 'YOU', 'NOT', 'ARE', 'WAS', 'BUT'}
            codes = [c for c in codes if c not in false_positives]
            if len(codes) >= 2:
                data['departure_airport'] = codes[0]
                data['arrival_airport'] = codes[1]
        
        return data if data else None
