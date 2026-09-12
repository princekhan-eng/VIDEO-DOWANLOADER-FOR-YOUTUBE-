import sys
from pathlib import Path

# Add project root directory to sys.path so server module is resolved
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import the FastAPI application instance for Vercel Python Serverless Runtime
from server import app
