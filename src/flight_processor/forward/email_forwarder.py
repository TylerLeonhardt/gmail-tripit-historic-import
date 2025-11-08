"""Email forwarding to TripIt"""
import base64
import logging
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from ..utils.retry import make_request_with_backoff
from ..utils.dry_run import dry_run_safe

logger = logging.getLogger(__name__)


class EmailForwarder:
    """Forwards emails to TripIt"""
    
    def __init__(self, service, tripit_email='plans@tripit.com'):
        """
        Initialize email forwarder
        
        Args:
            service: Authenticated Gmail API service
            tripit_email: TripIt email address to forward to
        """
        self.service = service
        self.tripit_email = tripit_email
    
    def get_message_headers(self, message):
        """Extract subject and other headers from message"""
        headers = {}
        if 'payload' in message and 'headers' in message['payload']:
            for header in message['payload']['headers']:
                name = header['name'].lower()
                if name == 'subject':
                    headers['subject'] = header['value']
                elif name == 'from':
                    headers['from'] = header['value']
                elif name == 'date':
                    headers['date'] = header['value']
        return headers
    
    @dry_run_safe(return_value={'id': 'dry-run-message-id'})
    def forward_message(self, message_id):
        """
        Forward a message to TripIt
        
        Args:
            message_id: Gmail message ID to forward
        
        Returns:
            Sent message object from Gmail API
        """
        logger.info(f"Forwarding message {message_id} to {self.tripit_email}")
        
        # Get the original message in raw format
        def get_raw_message():
            return self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='raw'
            ).execute()
        
        original = make_request_with_backoff(get_raw_message)
        
        # Decode the raw message
        msg_str = base64.urlsafe_b64decode(original['raw'].encode('ASCII'))
        
        # Get message headers for subject
        def get_full_message():
            return self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
        
        full_message = make_request_with_backoff(get_full_message)
        headers = self.get_message_headers(full_message)
        original_subject = headers.get('subject', 'Flight Confirmation')
        
        # Create forward message
        forward_msg = MIMEMultipart()
        forward_msg['to'] = self.tripit_email
        forward_msg['subject'] = f'Fwd: {original_subject}'
        
        # Attach the original message
        body_text = f'---------- Forwarded message ---------\n{msg_str.decode("utf-8", errors="ignore")}'
        body = MIMEText(body_text)
        forward_msg.attach(body)
        
        # Encode and send
        raw = base64.urlsafe_b64encode(forward_msg.as_bytes()).decode()
        send_message = {'raw': raw}
        
        def send_email():
            return self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()
        
        result = make_request_with_backoff(send_email)
        logger.info(f"Successfully forwarded message {message_id}")
        
        return result
    
    def forward_messages_batch(self, message_ids, batch_size=50, delay_between_batches=1):
        """
        Forward multiple messages in batches
        
        Args:
            message_ids: List of message IDs to forward
            batch_size: Number of messages per batch
            delay_between_batches: Seconds to wait between batches
        
        Returns:
            Dict with success and failure counts
        """
        logger.info(f"Forwarding {len(message_ids)} messages in batches of {batch_size}")
        
        results = {
            'success': 0,
            'failed': 0,
            'failed_ids': []
        }
        
        for i in range(0, len(message_ids), batch_size):
            batch = message_ids[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(message_ids) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} messages)")
            
            for msg_id in batch:
                try:
                    self.forward_message(msg_id)
                    results['success'] += 1
                except Exception as e:
                    logger.error(f"Failed to forward message {msg_id}: {e}")
                    results['failed'] += 1
                    results['failed_ids'].append(msg_id)
                
                # Small delay between individual messages
                time.sleep(0.1)
            
            # Delay between batches
            if i + batch_size < len(message_ids):
                logger.info(f"Waiting {delay_between_batches}s before next batch...")
                time.sleep(delay_between_batches)
        
        logger.info(f"Forwarding complete: {results['success']} succeeded, {results['failed']} failed")
        return results
