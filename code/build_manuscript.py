#!/usr/bin/env python3
"""Current manuscript entry point; prior v2 builder is retained separately."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).with_name('build_manuscript_v3.py')),run_name='__main__')
