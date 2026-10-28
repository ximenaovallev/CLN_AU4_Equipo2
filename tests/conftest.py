import sys
from pathlib import Path

# Permite "from cargar_csv import load_fixture" y "from app..." desde tests/.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
