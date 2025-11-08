"""Logging configuration utilities"""
import logging
import logging.config
from pathlib import Path


def setup_logging(log_level='INFO', log_file='logs/processor.log'):
    """Configure logging with both console and file handlers"""
    
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(levelname)-8s | %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'simple'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': log_file,
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            }
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console', 'file']
        }
    }
    
    logging.config.dictConfig(config)
    return logging.getLogger(__name__)
