import logging
import logging.config
from typing import Dict, Any
import sys
from pathlib import Path

class Logger:
    """Centralized logging configuration"""

    _instance = None
    _configured = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._configured:
            self.configure_logging()
            self._configured = True

    def configure_logging(self):
        """Configure logging with multiple handlers"""

        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Logging configuration
        config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'detailed': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },
                'simple': {
                    'format': '%(asctime)s - %(levelname)s - %(message)s',
                    'datefmt': '%H:%M:%S'
                },
                'json': {
                    'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
                    'datefmt': '%Y-%m-%dT%H:%M:%S'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'INFO',
                    'formatter': 'simple',
                    'stream': sys.stdout
                },
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'DEBUG',
                    'formatter': 'detailed',
                    'filename': 'logs/bybit_trader.log',
                    'maxBytes': 10 * 1024 * 1024,  # 10MB
                    'backupCount': 5
                },
                'error_file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'ERROR',
                    'formatter': 'detailed',
                    'filename': 'logs/errors.log',
                    'maxBytes': 10 * 1024 * 1024,  # 10MB
                    'backupCount': 3
                },
                'json_file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'INFO',
                    'formatter': 'json',
                    'filename': 'logs/bybit_trader.json',
                    'maxBytes': 10 * 1024 * 1024,  # 10MB
                    'backupCount': 3
                }
            },
            'root': {
                'level': 'DEBUG',
                'handlers': ['console', 'file', 'error_file']
            },
            'loggers': {
                'bybit_trader': {
                    'level': 'DEBUG',
                    'handlers': ['console', 'file', 'error_file', 'json_file'],
                    'propagate': False
                },
                'sqlalchemy': {
                    'level': 'WARNING',
                    'handlers': ['file'],
                    'propagate': False
                },
                'httpx': {
                    'level': 'WARNING',
                    'handlers': ['file'],
                    'propagate': False
                }
            }
        }

        logging.config.dictConfig(config)

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get logger instance"""
        return logging.getLogger(f"bybit_trader.{name}")

# Global logger instance
logger = Logger()

def get_logger(name: str) -> logging.Logger:
    """Convenience function to get logger"""
    return logger.get_logger(name)