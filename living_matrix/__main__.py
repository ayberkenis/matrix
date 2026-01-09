"""Main entry point for Living Matrix."""

import sys
import argparse
import uvicorn

from .api.app import create_app


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Living Matrix simulation")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode (legacy)")
    parser.add_argument("--no-run", action="store_true", help="[CLI mode] Start with autopilot paused")
    
    args = parser.parse_args()
    
    if args.cli:
        # Legacy CLI mode
        from living_matrix.core import Simulation
        autopilot_enabled = not args.no_run
        sim = Simulation(autopilot_enabled=autopilot_enabled)
        sim.run()
    else:
        # FastAPI server mode (default)
        app = create_app()
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info"
        )


if __name__ == "__main__":
    main()
