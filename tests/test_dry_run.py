"""Tests for dry-run functionality"""
import pytest
from flight_processor.utils.dry_run import DryRunManager, dry_run_safe


class TestDryRunManager:
    """Test DryRunManager class"""
    
    def setup_method(self):
        """Reset dry-run state before each test"""
        DryRunManager.disable()
    
    def test_enable_disable(self):
        """Test enabling and disabling dry-run mode"""
        assert not DryRunManager.is_enabled()
        
        DryRunManager.enable()
        assert DryRunManager.is_enabled()
        
        DryRunManager.disable()
        assert not DryRunManager.is_enabled()
    
    def test_dry_run_safe_decorator_enabled(self):
        """Test decorator when dry-run is enabled"""
        call_count = []
        
        @dry_run_safe(return_value="dry-run-result")
        def test_function():
            call_count.append(1)
            return "real-result"
        
        DryRunManager.enable()
        result = test_function()
        
        assert result == "dry-run-result"
        assert len(call_count) == 0  # Function should not be called
    
    def test_dry_run_safe_decorator_disabled(self):
        """Test decorator when dry-run is disabled"""
        call_count = []
        
        @dry_run_safe(return_value="dry-run-result")
        def test_function():
            call_count.append(1)
            return "real-result"
        
        DryRunManager.disable()
        result = test_function()
        
        assert result == "real-result"
        assert len(call_count) == 1  # Function should be called
    
    def test_dry_run_safe_with_args(self):
        """Test decorator with function arguments"""
        @dry_run_safe(return_value=None)
        def add(a, b):
            return a + b
        
        DryRunManager.disable()
        assert add(2, 3) == 5
        
        DryRunManager.enable()
        assert add(2, 3) is None
