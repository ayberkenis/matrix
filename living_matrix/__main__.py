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
    parser.add_argument("--fresh", action="store_true", help="Reset database and start fresh (clears all snapshots and metrics)")
    
    args = parser.parse_args()
    
    # Handle --fresh flag: reset database before starting
    if args.fresh:
        try:
            from living_matrix.db.migrations import initialize_database
            print("Resetting database...")
            initialize_database(fresh=True)
            print("Database reset complete. Starting fresh simulation.")
        except Exception as e:
            print(f"Warning: Could not reset database: {e}")
            print("Continuing with existing database...")
    
    if args.cli:
        # Legacy CLI mode
        from living_matrix.core import Simulation
        autopilot_enabled = not args.no_run
        sim = Simulation(autopilot_enabled=autopilot_enabled, fresh=args.fresh)
        sim.run()
    else:
        # FastAPI server mode (default)
        # Pass fresh flag to app creation
        app = create_app(fresh=args.fresh)
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info"
        )


if __name__ == "__main__":
    main()
