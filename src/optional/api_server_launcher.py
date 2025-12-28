#!/usr/bin/env python3
"""Optional API server launcher for Repository Intelligence Scanner."""

import os
import sys
import uvicorn
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    """Launch the API server."""
    try:
        from src.optional.api_server import app
        from src.optional.optional_config import get_feature_config

        config = get_feature_config("api_server")

        print("🚀 Starting Repository Intelligence Scanner API Server")
        print(f"📍 Host: {config['host']}")
        print(f"🔌 Port: {config['port']}")
        print(f"👷 Workers: {config['workers']}")
        print("⚠️  Note: API server may violate core spec compliance")
        print("   Spec requires offline operation with no external services")
        print()

        uvicorn.run(
            "src.optional.api_server:app",
            host=config["host"],
            port=config["port"],
            workers=config["workers"],
            reload=False
        )

    except ImportError as e:
        print(f"❌ Error: API server components not available: {e}")
        print("Make sure optional features are properly installed.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting API server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()