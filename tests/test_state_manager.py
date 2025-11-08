"""Tests for state manager"""
import pytest
import tempfile
import os
from flight_processor.state.database import init_database
from flight_processor.state.state_manager import StateManager


class TestStateManager:
    """Test StateManager"""
    
    def setup_method(self):
        """Setup temp database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        init_database(self.db_path)
        self.state_manager = StateManager(self.db_path)
    
    def teardown_method(self):
        """Cleanup temp database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_save_and_get_email(self):
        """Test saving and retrieving email"""
        self.state_manager.save_email(
            message_id='msg123',
            thread_id='thread123',
            subject='Test Email',
            from_email='test@example.com',
            pnr='ABC123',
            flight_number='UA456'
        )
        
        email = self.state_manager.get_email('msg123')
        
        assert email is not None
        assert email['message_id'] == 'msg123'
        assert email['subject'] == 'Test Email'
        assert email['pnr'] == 'ABC123'
        assert email['flight_number'] == 'UA456'
    
    def test_is_email_processed(self):
        """Test checking if email is processed"""
        self.state_manager.save_email(message_id='msg123')
        
        # Not processed yet
        assert not self.state_manager.is_email_processed('msg123', 'PHASE1_LABEL')
        
        # Mark as processed
        self.state_manager.mark_email_processed('msg123', 'PHASE1_LABEL', 'SUCCESS')
        
        # Should be processed now
        assert self.state_manager.is_email_processed('msg123', 'PHASE1_LABEL')
        
        # Different phase should not be processed
        assert not self.state_manager.is_email_processed('msg123', 'PHASE2_FORWARD')
    
    def test_mark_email_processed_with_error(self):
        """Test marking email as failed with error message"""
        self.state_manager.save_email(message_id='msg123')
        self.state_manager.mark_email_processed(
            'msg123', 
            'PHASE1_LABEL', 
            'FAILED',
            'Parse error'
        )
        
        # Should not be marked as successfully processed
        assert not self.state_manager.is_email_processed('msg123', 'PHASE1_LABEL')
    
    def test_get_processing_stats(self):
        """Test getting processing statistics"""
        # Add some test data
        self.state_manager.save_email(message_id='msg1')
        self.state_manager.save_email(message_id='msg2')
        self.state_manager.save_email(message_id='msg3')
        
        self.state_manager.mark_email_processed('msg1', 'PHASE1_LABEL', 'SUCCESS')
        self.state_manager.mark_email_processed('msg2', 'PHASE1_LABEL', 'SUCCESS')
        self.state_manager.mark_email_processed('msg3', 'PHASE1_LABEL', 'FAILED')
        
        stats = self.state_manager.get_processing_stats('PHASE1_LABEL')
        
        # Find SUCCESS and FAILED counts
        success_stat = next((s for s in stats if s['status'] == 'SUCCESS'), None)
        failed_stat = next((s for s in stats if s['status'] == 'FAILED'), None)
        
        assert success_stat is not None
        assert success_stat['count'] == 2
        assert failed_stat is not None
        assert failed_stat['count'] == 1
    
    def test_save_and_get_checkpoint(self):
        """Test saving and retrieving checkpoints"""
        self.state_manager.save_checkpoint(
            last_message_id='msg100',
            status='COMPLETED',
            failed_message_ids=['msg5', 'msg10'],
            message='Batch complete'
        )
        
        checkpoint = self.state_manager.get_last_checkpoint()
        
        assert checkpoint is not None
        assert checkpoint['last_synced_message_id'] == 'msg100'
        assert checkpoint['status'] == 'COMPLETED'
        assert 'msg5' in checkpoint['failed_message_ids']
    
    def test_get_unprocessed_emails(self):
        """Test getting unprocessed emails"""
        # Add emails
        self.state_manager.save_email(message_id='msg1')
        self.state_manager.save_email(message_id='msg2')
        self.state_manager.save_email(message_id='msg3')
        
        # Process one
        self.state_manager.mark_email_processed('msg1', 'PHASE1_LABEL', 'SUCCESS')
        
        # Get unprocessed
        unprocessed = self.state_manager.get_unprocessed_emails('PHASE1_LABEL')
        
        assert len(unprocessed) == 2
        message_ids = [e['message_id'] for e in unprocessed]
        assert 'msg2' in message_ids
        assert 'msg3' in message_ids
        assert 'msg1' not in message_ids
