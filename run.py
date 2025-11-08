#!/usr/bin/env python3
"""
Wrapper script to run the Gmail-TripIt Historic Import System
"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from flight_processor.main import main

if __name__ == '__main__':
    main()
