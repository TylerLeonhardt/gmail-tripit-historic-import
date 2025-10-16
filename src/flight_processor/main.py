"""Main entry point for Gmail-TripIt Historic Import System"""
import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from flight_processor.utils import setup_logging, DryRunManager
from flight_processor.auth import GmailAuthenticator
from flight_processor.search import EmailSearcher
from flight_processor.parsers import FlightClassifier, FlightParser
from flight_processor.dedup import Deduplicator
from flight_processor.forward import EmailForwarder, LabelManager
from flight_processor.state import init_database, StateManager

logger = logging.getLogger(__name__)


def extract_email_content(message):
    """Extract content from Gmail message"""
    email_data = {
        'message_id': message['id'],
        'thread_id': message.get('threadId'),
        'subject': '',
        'from_email': '',
        'msg_date': '',
        'html_content': '',
        'text_content': ''
    }
    
    # Extract headers
    if 'payload' in message and 'headers' in message['payload']:
        for header in message['payload']['headers']:
            name = header['name'].lower()
            if name == 'subject':
                email_data['subject'] = header['value']
            elif name == 'from':
                email_data['from_email'] = header['value']
            elif name == 'date':
                email_data['msg_date'] = header['value']
    
    # Extract body
    def extract_parts(payload):
        if 'parts' in payload:
            for part in payload['parts']:
                extract_parts(part)
        elif 'body' in payload and 'data' in payload['body']:
            mime_type = payload.get('mimeType', '')
            import base64
            data = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
            
            if mime_type == 'text/html':
                email_data['html_content'] += data
            elif mime_type == 'text/plain':
                email_data['text_content'] += data
    
    if 'payload' in message:
        extract_parts(message['payload'])
    
    return email_data


def phase1_label_emails(args, service, state_manager):
    """Phase 1: Search, classify, parse, and label flight emails"""
    logger.info("=" * 80)
    logger.info("PHASE 1: Labeling Flight Confirmation Emails")
    logger.info("=" * 80)
    
    # Initialize components
    searcher = EmailSearcher(service)
    classifier = FlightClassifier()
    parser = FlightParser()
    label_manager = LabelManager(service)
    
    # Get or create label
    label_id = label_manager.get_or_create_label(args.label_name)
    
    # Search for emails
    logger.info(f"Searching with query: {args.query[:100]}...")
    message_list = searcher.list_messages_with_pagination(query=args.query)
    
    if not message_list:
        logger.info("No messages found matching the query")
        return
    
    logger.info(f"Found {len(message_list)} messages to process")
    
    # Process each message
    flight_messages = []
    
    for i, msg_ref in enumerate(message_list, 1):
        msg_id = msg_ref['id']
        
        # Check if already processed
        if state_manager.is_email_processed(msg_id, 'PHASE1_LABEL'):
            logger.debug(f"Message {msg_id} already processed, skipping")
            continue
        
        if i % 100 == 0:
            logger.info(f"Processing message {i}/{len(message_list)}...")
        
        try:
            # Fetch full message
            message = searcher.get_message(msg_id, format='full')
            email_data = extract_email_content(message)
            
            # Classify
            is_flight, score = classifier.classify(email_data)
            
            if is_flight:
                logger.info(f"✓ Flight confirmation detected: {email_data['subject'][:60]}")
                
                # Parse flight details
                flight_details = parser.parse(email_data)
                
                if flight_details:
                    email_data.update(flight_details)
                    logger.info(f"  Parsed: PNR={flight_details.get('booking_reference', 'N/A')}, "
                              f"Flight={flight_details.get('flight_number', 'N/A')}")
                
                # Save to database
                state_manager.save_email(
                    message_id=msg_id,
                    thread_id=email_data.get('thread_id'),
                    subject=email_data.get('subject'),
                    from_email=email_data.get('from_email'),
                    msg_date=email_data.get('msg_date'),
                    pnr=flight_details.get('booking_reference') if flight_details else None,
                    flight_number=flight_details.get('flight_number') if flight_details else None,
                    departure_airport=flight_details.get('departure_airport') if flight_details else None,
                    arrival_airport=flight_details.get('arrival_airport') if flight_details else None
                )
                
                flight_messages.append(msg_id)
                state_manager.mark_email_processed(msg_id, 'PHASE1_LABEL', 'SUCCESS')
            else:
                logger.debug(f"✗ Not a flight confirmation: {email_data['subject'][:60]}")
                state_manager.mark_email_processed(msg_id, 'PHASE1_LABEL', 'SKIPPED')
        
        except Exception as e:
            logger.error(f"Error processing message {msg_id}: {e}")
            state_manager.mark_email_processed(msg_id, 'PHASE1_LABEL', 'FAILED', str(e))
    
    logger.info(f"\nIdentified {len(flight_messages)} flight confirmation emails")
    
    if flight_messages and not DryRunManager.is_enabled():
        # Apply labels
        logger.info(f"Applying label '{args.label_name}' to {len(flight_messages)} emails...")
        label_manager.apply_label_to_messages(flight_messages, label_id)
    
    logger.info("Phase 1 complete!")
    logger.info("=" * 80)


def phase2_forward_emails(args, service, state_manager):
    """Phase 2: Forward labeled emails to TripIt"""
    logger.info("=" * 80)
    logger.info("PHASE 2: Forwarding Emails to TripIt")
    logger.info("=" * 80)
    
    # Get emails that were successfully labeled but not yet forwarded
    emails = state_manager.get_unprocessed_emails('PHASE2_FORWARD')
    
    if not emails:
        logger.info("No emails to forward")
        return
    
    logger.info(f"Found {len(emails)} emails to forward")
    
    # Deduplicate
    if args.deduplicate:
        deduplicator = Deduplicator(fuzzy_threshold=95)
        unique_emails = deduplicator.get_unique_emails(emails)
        logger.info(f"After deduplication: {len(unique_emails)} unique emails")
        message_ids = [e['message_id'] for e in unique_emails]
    else:
        message_ids = [e['message_id'] for e in emails]
    
    # Forward emails
    forwarder = EmailForwarder(service, tripit_email=settings.TRIPIT_EMAIL)
    
    logger.info(f"Forwarding {len(message_ids)} emails to {settings.TRIPIT_EMAIL}...")
    
    for msg_id in message_ids:
        try:
            forwarder.forward_message(msg_id)
            state_manager.mark_email_processed(msg_id, 'PHASE2_FORWARD', 'SUCCESS')
        except Exception as e:
            logger.error(f"Failed to forward {msg_id}: {e}")
            state_manager.mark_email_processed(msg_id, 'PHASE2_FORWARD', 'FAILED', str(e))
    
    logger.info("Phase 2 complete!")
    logger.info("=" * 80)


def show_stats(state_manager):
    """Display processing statistics"""
    logger.info("=" * 80)
    logger.info("PROCESSING STATISTICS")
    logger.info("=" * 80)
    
    stats = state_manager.get_processing_stats()
    
    for stat in stats:
        phase = stat.get('phase', 'Unknown')
        status = stat.get('status', 'Unknown')
        count = stat.get('count', 0)
        logger.info(f"{phase:20s} | {status:10s} | {count:5d}")
    
    logger.info("=" * 80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Gmail to TripIt Historic Flight Import System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run of phase 1 (label emails)
  python -m flight_processor.main --phase 1 --dry-run
  
  # Actually run phase 1
  python -m flight_processor.main --phase 1
  
  # Run phase 2 (forward to TripIt) with dry run
  python -m flight_processor.main --phase 2 --dry-run
  
  # Run both phases
  python -m flight_processor.main --phase all
  
  # Show statistics
  python -m flight_processor.main --stats
        """
    )
    
    parser.add_argument('--phase', choices=['1', '2', 'all'], default='all',
                       help='Which phase to run (default: all)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Perform a dry run without making actual changes')
    parser.add_argument('--query', default=settings.SEARCH_QUERY,
                       help='Gmail search query (default from settings)')
    parser.add_argument('--label-name', default='Flight Confirmations - To Review',
                       help='Gmail label name to apply (default: Flight Confirmations - To Review)')
    parser.add_argument('--deduplicate', action='store_true', default=True,
                       help='Remove duplicates before forwarding (default: True)')
    parser.add_argument('--no-deduplicate', dest='deduplicate', action='store_false',
                       help='Do not remove duplicates before forwarding')
    parser.add_argument('--stats', action='store_true',
                       help='Show processing statistics and exit')
    parser.add_argument('--log-level', default=settings.LOG_LEVEL,
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level=args.log_level, log_file=settings.LOG_FILE)
    
    # Enable dry-run mode if requested
    if args.dry_run:
        DryRunManager.enable()
    
    logger.info("Gmail-TripIt Historic Import System")
    logger.info(f"Dry-run mode: {DryRunManager.is_enabled()}")
    
    # Initialize database
    init_database(settings.DB_PATH)
    state_manager = StateManager(settings.DB_PATH)
    
    # Show stats and exit if requested
    if args.stats:
        show_stats(state_manager)
        return
    
    # Authenticate with Gmail
    authenticator = GmailAuthenticator(
        scopes=settings.SCOPES,
        credentials_file=settings.CREDENTIALS_FILE,
        token_file=settings.TOKEN_FILE
    )
    service = authenticator.authenticate()
    
    # Run requested phases
    if args.phase in ['1', 'all']:
        phase1_label_emails(args, service, state_manager)
    
    if args.phase in ['2', 'all']:
        phase2_forward_emails(args, service, state_manager)
    
    # Show final stats
    show_stats(state_manager)
    
    logger.info("All operations complete!")


if __name__ == '__main__':
    main()
