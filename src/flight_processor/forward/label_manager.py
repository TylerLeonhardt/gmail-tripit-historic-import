"""Label management for Gmail"""
import logging
from ..utils.retry import make_request_with_backoff
from ..utils.dry_run import dry_run_safe

logger = logging.getLogger(__name__)


class LabelManager:
    """Manages Gmail labels"""
    
    def __init__(self, service):
        """
        Initialize label manager
        
        Args:
            service: Authenticated Gmail API service
        """
        self.service = service
    
    def get_or_create_label(self, label_name):
        """
        Get existing label or create new one
        
        Args:
            label_name: Name of the label
        
        Returns:
            Label ID
        """
        logger.info(f"Getting or creating label: {label_name}")
        
        # List existing labels
        def list_labels():
            return self.service.users().labels().list(userId='me').execute()
        
        result = make_request_with_backoff(list_labels)
        labels = result.get('labels', [])
        
        # Check if label exists
        for label in labels:
            if label['name'] == label_name:
                logger.info(f"Label '{label_name}' already exists with ID: {label['id']}")
                return label['id']
        
        # Create new label
        logger.info(f"Creating new label: {label_name}")
        label_object = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        
        def create_label():
            return self.service.users().labels().create(
                userId='me',
                body=label_object
            ).execute()
        
        created_label = make_request_with_backoff(create_label)
        logger.info(f"Created label '{label_name}' with ID: {created_label['id']}")
        
        return created_label['id']
    
    @dry_run_safe(return_value=None)
    def apply_label_to_messages(self, message_ids, label_id, batch_size=1000):
        """
        Apply label to multiple messages using batch operations
        
        Args:
            message_ids: List of message IDs
            label_id: Label ID to apply
            batch_size: Number of messages per batch (max 1000)
        
        Returns:
            Number of messages labeled
        """
        logger.info(f"Applying label to {len(message_ids)} messages...")
        
        labeled_count = 0
        
        for i in range(0, len(message_ids), batch_size):
            batch = message_ids[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(message_ids) + batch_size - 1) // batch_size
            
            logger.info(f"Labeling batch {batch_num}/{total_batches} ({len(batch)} messages)")
            
            body = {
                'ids': batch,
                'addLabelIds': [label_id],
                'removeLabelIds': []
            }
            
            def batch_modify():
                return self.service.users().messages().batchModify(
                    userId='me',
                    body=body
                ).execute()
            
            make_request_with_backoff(batch_modify)
            labeled_count += len(batch)
            
            logger.info(f"Labeled {labeled_count}/{len(message_ids)} messages")
        
        logger.info(f"Successfully labeled {labeled_count} messages")
        return labeled_count
