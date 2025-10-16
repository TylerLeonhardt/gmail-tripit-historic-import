"""Gmail email search functionality"""
import logging
import time
from ..utils.retry import make_request_with_backoff

logger = logging.getLogger(__name__)


class EmailSearcher:
    """Searches Gmail for messages with pagination support"""
    
    def __init__(self, service):
        """
        Initialize email searcher
        
        Args:
            service: Authenticated Gmail API service
        """
        self.service = service
    
    def list_messages_with_pagination(self, query='', max_results=500):
        """
        Search Gmail messages with pagination
        
        Args:
            query: Gmail search query string
            max_results: Maximum results per page (max 500)
        
        Returns:
            List of message objects with id and threadId
        """
        logger.info(f"Searching emails with query: {query[:100]}...")
        messages = []
        page_token = None
        page_num = 0
        
        while True:
            page_num += 1
            logger.debug(f"Fetching page {page_num}...")
            
            def fetch_page():
                return self.service.users().messages().list(
                    userId='me',
                    q=query,
                    pageToken=page_token,
                    maxResults=max_results
                ).execute()
            
            results = make_request_with_backoff(fetch_page)
            
            if 'messages' in results:
                page_messages = results['messages']
                messages.extend(page_messages)
                logger.info(f"Page {page_num}: Found {len(page_messages)} messages (total: {len(messages)})")
            else:
                logger.info(f"Page {page_num}: No messages found")
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
            
            # Small delay between pages to be nice to the API
            time.sleep(0.1)
        
        logger.info(f"Search complete: Found {len(messages)} total messages")
        return messages
    
    def get_message(self, message_id, format='full'):
        """
        Get a single message by ID
        
        Args:
            message_id: Message ID
            format: Format to retrieve (full, metadata, raw, minimal)
        
        Returns:
            Message object
        """
        def fetch_message():
            return self.service.users().messages().get(
                userId='me',
                id=message_id,
                format=format
            ).execute()
        
        return make_request_with_backoff(fetch_message)
    
    def get_messages_batch(self, message_ids, format='full'):
        """
        Get multiple messages (note: this doesn't use batch API, 
        but retrieves them sequentially with rate limiting)
        
        Args:
            message_ids: List of message IDs
            format: Format to retrieve
        
        Returns:
            List of message objects
        """
        logger.info(f"Fetching {len(message_ids)} messages...")
        messages = []
        
        for i, msg_id in enumerate(message_ids, 1):
            if i % 100 == 0:
                logger.info(f"Fetched {i}/{len(message_ids)} messages...")
            
            try:
                msg = self.get_message(msg_id, format=format)
                messages.append(msg)
            except Exception as e:
                logger.error(f"Failed to fetch message {msg_id}: {e}")
            
            # Small delay to avoid rate limits
            if i % 10 == 0:
                time.sleep(0.1)
        
        logger.info(f"Successfully fetched {len(messages)}/{len(message_ids)} messages")
        return messages
