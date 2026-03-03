"""Module entry point for python -m mike.

Allows running Mike as a module: python -m mike
"""

import sys
from mike.cli import main

if __name__ == "__main__":
    main()
