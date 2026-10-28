#!/usr/bin/env python3
"""Current manuscript entry point for the final 261028_v3 release."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).with_name('build_manuscript_v3.py')),run_name='__main__')
