"""Store the packaged application's database alongside the executable."""
import os
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    os.environ.setdefault(
        'DISCIPLINE_DB_PATH',
        str(Path(sys.executable).resolve().parent / 'database' / 'discipline.db'),
    )
    Path(os.environ['DISCIPLINE_DB_PATH']).parent.mkdir(parents=True, exist_ok=True)
