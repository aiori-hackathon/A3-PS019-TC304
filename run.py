"""
Root execution script for DataPulse.
Run: python run.py
"""
import sys
import uvicorn
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.config import SERVER_HOST, SERVER_PORT

if __name__ == "__main__":
    print(f"[*] Starting DataPulse on http://{SERVER_HOST}:{SERVER_PORT}")
    uvicorn.run("src.backend.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)
