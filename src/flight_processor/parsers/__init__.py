"""Parsers package"""
from .classifier import FlightClassifier
from .flight_parser import FlightParser

# AIParser is optional and only available if anthropic is installed
try:
    from .ai_parser import AIParser
    __all__ = ['FlightClassifier', 'FlightParser', 'AIParser']
except ImportError:
    __all__ = ['FlightClassifier', 'FlightParser']
