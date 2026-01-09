"""CLI entry point for Living Matrix."""

import sys
import argparse

from .core import Simulation


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Living Matrix - Autonomous World Simulation")
    parser.add_argument(
        "--no-run",
        action="store_true",
        help="Start with autopilot paused (default: autopilot runs automatically)"
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Explicitly start autopilot (this is the default)"
    )
    
    args = parser.parse_args()
    
    # Default is to run (autopilot enabled)
    autopilot_enabled = not args.no_run
    
    sim = Simulation(autopilot_enabled=autopilot_enabled)
    sim.run()


if __name__ == "__main__":
    main()
