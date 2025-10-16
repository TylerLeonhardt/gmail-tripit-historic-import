"""Duplicate detection module"""
import logging
from fuzzywuzzy import fuzz

logger = logging.getLogger(__name__)


class Deduplicator:
    """Detects duplicate flight confirmations"""
    
    def __init__(self, fuzzy_threshold=95):
        """
        Initialize deduplicator
        
        Args:
            fuzzy_threshold: Similarity threshold for fuzzy matching (0-100)
        """
        self.fuzzy_threshold = fuzzy_threshold
    
    def are_pnrs_duplicate(self, pnr1, pnr2):
        """
        Check if two PNRs are duplicates using fuzzy matching
        
        Args:
            pnr1: First PNR
            pnr2: Second PNR
        
        Returns:
            True if PNRs are likely duplicates
        """
        if not pnr1 or not pnr2:
            return False
        
        # Exact match
        if pnr1.upper() == pnr2.upper():
            return True
        
        # Fuzzy match
        score = fuzz.ratio(pnr1.upper(), pnr2.upper())
        return score >= self.fuzzy_threshold
    
    def find_duplicates(self, emails):
        """
        Find duplicate emails based on PNR matching
        
        Args:
            emails: List of email dicts with 'message_id' and 'pnr' fields
        
        Returns:
            Dict mapping PNR to list of duplicate message IDs
        """
        logger.info(f"Checking {len(emails)} emails for duplicates...")
        
        duplicates = {}
        processed_pnrs = {}
        
        for email in emails:
            message_id = email.get('message_id')
            pnr = email.get('pnr')
            
            if not pnr:
                continue
            
            pnr_upper = pnr.upper()
            found_duplicate = False
            
            # Check against already processed PNRs
            for known_pnr, msg_ids in list(processed_pnrs.items()):
                if self.are_pnrs_duplicate(pnr_upper, known_pnr):
                    # Found a duplicate group
                    msg_ids.append(message_id)
                    if known_pnr not in duplicates:
                        duplicates[known_pnr] = msg_ids
                    found_duplicate = True
                    break
            
            if not found_duplicate:
                # Start a new PNR group
                processed_pnrs[pnr_upper] = [message_id]
        
        # Filter to only groups with actual duplicates (2+ emails)
        duplicates = {pnr: ids for pnr, ids in duplicates.items() if len(ids) > 1}
        
        duplicate_count = sum(len(ids) for ids in duplicates.values())
        logger.info(f"Found {len(duplicates)} duplicate groups containing {duplicate_count} emails")
        
        return duplicates
    
    def get_unique_emails(self, emails):
        """
        Get unique emails (first occurrence of each PNR)
        
        Args:
            emails: List of email dicts with 'message_id' and 'pnr' fields
        
        Returns:
            List of unique email dicts
        """
        seen_pnrs = set()
        unique_emails = []
        
        for email in emails:
            pnr = email.get('pnr', '').upper() if email.get('pnr') else None
            
            # If no PNR, keep the email (can't deduplicate)
            if not pnr:
                unique_emails.append(email)
                continue
            
            # Check if we've seen a similar PNR
            is_duplicate = False
            for seen_pnr in seen_pnrs:
                if self.are_pnrs_duplicate(pnr, seen_pnr):
                    is_duplicate = True
                    logger.debug(f"Skipping duplicate PNR: {pnr} (matches {seen_pnr})")
                    break
            
            if not is_duplicate:
                seen_pnrs.add(pnr)
                unique_emails.append(email)
        
        logger.info(f"Filtered to {len(unique_emails)} unique emails from {len(emails)} total")
        return unique_emails
