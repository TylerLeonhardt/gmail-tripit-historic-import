"""Dry-run mode manager"""
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class DryRunManager:
    """Global dry-run state manager"""
    _enabled = False
    
    @classmethod
    def enable(cls):
        """Enable dry-run mode"""
        cls._enabled = True
        logger.info("DRY-RUN MODE ENABLED - No actual changes will be made")
    
    @classmethod
    def disable(cls):
        """Disable dry-run mode"""
        cls._enabled = False
    
    @classmethod
    def is_enabled(cls):
        """Check if dry-run mode is enabled"""
        return cls._enabled


def dry_run_safe(return_value=None):
    """
    Decorator to make functions dry-run safe.
    When dry-run is enabled, log the action but don't execute it.
    
    Args:
        return_value: Value to return when in dry-run mode
    
    Example:
        @dry_run_safe(return_value=True)
        def apply_label(service, msg_id, label_id):
            # This will only execute if NOT in dry-run mode
            service.users().messages().modify(
                userId='me', id=msg_id, body={'addLabelIds': [label_id]}
            ).execute()
            return True
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if DryRunManager.is_enabled():
                # Extract function name and arguments for logging
                func_name = func.__name__
                args_str = ', '.join([str(arg)[:50] for arg in args[:3]])
                logger.info(f"[DRY-RUN] Would call {func_name}({args_str}...)")
                return return_value
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator
