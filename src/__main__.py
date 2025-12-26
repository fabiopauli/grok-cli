#!/usr/bin/env python3

"""
Entry point for grok-cli command.

This allows the package to be run as:
- grok-cli (after pip install)
- python -m src (development)
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import main
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import main

if __name__ == "__main__":
    main()
