"""Tests for deduplicator"""
import pytest
from flight_processor.dedup.deduplicator import Deduplicator


class TestDeduplicator:
    """Test Deduplicator"""
    
    def setup_method(self):
        """Setup deduplicator for each test"""
        self.dedup = Deduplicator(fuzzy_threshold=95)
    
    def test_exact_pnr_match(self):
        """Test exact PNR matching"""
        assert self.dedup.are_pnrs_duplicate('ABC123', 'ABC123')
        assert self.dedup.are_pnrs_duplicate('ABC123', 'abc123')  # Case insensitive
    
    def test_fuzzy_pnr_match(self):
        """Test fuzzy PNR matching"""
        # One character difference in 6-char PNR (~83% similarity) should not match at 95% threshold
        assert not self.dedup.are_pnrs_duplicate('ABC123', 'ABC124')
        
        # Very similar should match
        assert self.dedup.are_pnrs_duplicate('ABCDEF', 'ABCDEF')
    
    def test_no_pnr_returns_false(self):
        """Test that None or empty PNRs return False"""
        assert not self.dedup.are_pnrs_duplicate(None, 'ABC123')
        assert not self.dedup.are_pnrs_duplicate('ABC123', None)
        assert not self.dedup.are_pnrs_duplicate('', 'ABC123')
    
    def test_find_duplicates(self):
        """Test finding duplicate groups"""
        emails = [
            {'message_id': '1', 'pnr': 'ABC123'},
            {'message_id': '2', 'pnr': 'ABC123'},  # Duplicate
            {'message_id': '3', 'pnr': 'XYZ789'},
            {'message_id': '4', 'pnr': 'XYZ789'},  # Duplicate
            {'message_id': '5', 'pnr': 'DEF456'},  # Unique
        ]
        
        duplicates = self.dedup.find_duplicates(emails)
        
        # Should find 2 duplicate groups
        assert len(duplicates) == 2
        assert 'ABC123' in duplicates
        assert 'XYZ789' in duplicates
    
    def test_get_unique_emails(self):
        """Test getting unique emails"""
        emails = [
            {'message_id': '1', 'pnr': 'ABC123', 'subject': 'First'},
            {'message_id': '2', 'pnr': 'ABC123', 'subject': 'Duplicate'},
            {'message_id': '3', 'pnr': 'XYZ789', 'subject': 'Second'},
            {'message_id': '4', 'pnr': None, 'subject': 'No PNR'},
        ]
        
        unique = self.dedup.get_unique_emails(emails)
        
        # Should have 3 unique: first ABC123, XYZ789, and No PNR
        assert len(unique) == 3
        assert unique[0]['message_id'] == '1'
        assert unique[1]['message_id'] == '3'
        assert unique[2]['message_id'] == '4'
    
    def test_emails_without_pnr_kept(self):
        """Test that emails without PNR are kept"""
        emails = [
            {'message_id': '1', 'pnr': None},
            {'message_id': '2', 'pnr': ''},
            {'message_id': '3', 'pnr': 'ABC123'},
        ]
        
        unique = self.dedup.get_unique_emails(emails)
        
        # All should be kept since first two have no PNR
        assert len(unique) == 3
