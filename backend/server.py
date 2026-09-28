"""Compatibility entry point; prefer python3 app.py."""
import runpy
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
runpy.run_path(str(root / 'app.py'), run_name='__main__')
