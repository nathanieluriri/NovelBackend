import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT_STR = str(APP_ROOT)

if APP_ROOT_STR not in sys.path:
    sys.path.insert(0, APP_ROOT_STR)
