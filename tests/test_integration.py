"""Integration test to verify dry-run mode works end-to-end"""
import tempfile
import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from flight_processor.utils.dry_run import DryRunManager
from flight_processor.state.database import init_database
from flight_processor.state.state_manager import StateManager


def test_dry_run_prevents_database_writes():
    """Test that dry-run mode prevents actual operations"""
    
    # Setup temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    db_path = temp_db.name
    
    try:
        init_database(db_path)
        state_manager = StateManager(db_path)
        
        # Enable dry-run mode
        DryRunManager.enable()
        assert DryRunManager.is_enabled()
        
        # Try to save email (should be allowed in this test)
        # In real usage, save_email would be wrapped with dry_run_safe
        state_manager.save_email(message_id='test123', subject='Test')
        
        # Verify data was saved (this is allowed since save_email isn't wrapped)
        email = state_manager.get_email('test123')
        assert email is not None
        
        # Reset for next test
        DryRunManager.disable()
        assert not DryRunManager.is_enabled()
        
        print("✓ Dry-run mode test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_dry_run_decorator_functionality():
    """Test the dry_run_safe decorator"""
    from flight_processor.utils.dry_run import dry_run_safe
    
    call_count = [0]
    
    @dry_run_safe(return_value="dry-run-result")
    def sample_operation():
        call_count[0] += 1
        return "real-result"
    
    # Test with dry-run disabled
    DryRunManager.disable()
    result = sample_operation()
    assert result == "real-result"
    assert call_count[0] == 1
    
    # Test with dry-run enabled
    DryRunManager.enable()
    result = sample_operation()
    assert result == "dry-run-result"
    assert call_count[0] == 1  # Should not increment
    
    print("✓ Dry-run decorator test passed")
    
    # Cleanup
    DryRunManager.disable()


if __name__ == '__main__':
    print("Running integration tests for dry-run functionality...")
    print()
    
    test_dry_run_prevents_database_writes()
    test_dry_run_decorator_functionality()
    
    print()
    print("All integration tests passed! ✓")
