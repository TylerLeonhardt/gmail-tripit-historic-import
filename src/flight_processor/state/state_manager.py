"""State management for tracking email processing"""
import sqlite3
import json
import logging
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)


class StateManager:
    """Manages state tracking in SQLite database"""
    
    def __init__(self, db_path):
        """
        Initialize state manager
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def save_email(self, message_id, thread_id=None, subject=None, from_email=None,
                   msg_date=None, pnr=None, flight_number=None, 
                   departure_airport=None, arrival_airport=None):
        """
        Save email metadata to database
        
        Args:
            message_id: Gmail message ID
            thread_id: Gmail thread ID
            subject: Email subject
            from_email: Sender email address
            msg_date: Email date
            pnr: Parsed PNR/confirmation number
            flight_number: Parsed flight number
            departure_airport: Departure airport code
            arrival_airport: Arrival airport code
        """
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO emails 
                (message_id, thread_id, subject, from_email, msg_date, pnr, 
                 flight_number, departure_airport, arrival_airport)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (message_id, thread_id, subject, from_email, msg_date, pnr,
                  flight_number, departure_airport, arrival_airport))
    
    def get_email(self, message_id):
        """
        Get email metadata from database
        
        Args:
            message_id: Gmail message ID
        
        Returns:
            Email record or None
        """
        with self.get_connection() as conn:
            result = conn.execute("""
                SELECT * FROM emails WHERE message_id = ?
            """, (message_id,)).fetchone()
            return dict(result) if result else None
    
    def is_email_processed(self, message_id, phase):
        """
        Check if email has been processed in a given phase
        
        Args:
            message_id: Gmail message ID
            phase: Processing phase name
        
        Returns:
            True if already processed successfully
        """
        with self.get_connection() as conn:
            result = conn.execute("""
                SELECT 1 FROM processing_state
                WHERE message_id = ? AND phase = ? AND status = 'SUCCESS'
                LIMIT 1
            """, (message_id, phase)).fetchone()
            return result is not None
    
    def mark_email_processed(self, message_id, phase, status='SUCCESS', error_msg=None):
        """
        Mark email as processed in a given phase
        
        Args:
            message_id: Gmail message ID
            phase: Processing phase name
            status: Status (SUCCESS, FAILED, SKIPPED)
            error_msg: Error message if failed
        """
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO processing_state 
                (message_id, phase, status, error_message)
                VALUES (?, ?, ?, ?)
            """, (message_id, phase, status, error_msg))
    
    def get_processing_stats(self, phase=None):
        """
        Get processing statistics
        
        Args:
            phase: Optional phase to filter by
        
        Returns:
            Dict with status counts
        """
        with self.get_connection() as conn:
            if phase:
                query = """
                    SELECT status, COUNT(*) as count
                    FROM processing_state
                    WHERE phase = ?
                    GROUP BY status
                """
                results = conn.execute(query, (phase,)).fetchall()
            else:
                query = """
                    SELECT phase, status, COUNT(*) as count
                    FROM processing_state
                    GROUP BY phase, status
                """
                results = conn.execute(query).fetchall()
            
            return [dict(row) for row in results]
    
    def save_checkpoint(self, last_message_id, status='COMPLETED', 
                       failed_message_ids=None, message=None):
        """
        Save a checkpoint for resuming operations
        
        Args:
            last_message_id: Last processed message ID
            status: Checkpoint status
            failed_message_ids: List of failed message IDs
            message: Optional message
        """
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO sync_checkpoints 
                (last_synced_message_id, status, failed_message_ids, message)
                VALUES (?, ?, ?, ?)
            """, (last_message_id, status, json.dumps(failed_message_ids or []), message))
    
    def get_last_checkpoint(self):
        """
        Get the most recent checkpoint
        
        Returns:
            Checkpoint record or None
        """
        with self.get_connection() as conn:
            result = conn.execute("""
                SELECT * FROM sync_checkpoints
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()
            return dict(result) if result else None
    
    def get_unprocessed_emails(self, phase):
        """
        Get emails that haven't been processed in a given phase
        
        Args:
            phase: Processing phase name
        
        Returns:
            List of email records
        """
        with self.get_connection() as conn:
            results = conn.execute("""
                SELECT e.* FROM emails e
                WHERE NOT EXISTS (
                    SELECT 1 FROM processing_state ps
                    WHERE ps.message_id = e.message_id 
                    AND ps.phase = ? 
                    AND ps.status = 'SUCCESS'
                )
            """, (phase,)).fetchall()
            return [dict(row) for row in results]
