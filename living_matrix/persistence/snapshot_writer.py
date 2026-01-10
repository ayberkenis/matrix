"""Snapshot writer for world state persistence."""

import logging
from typing import Dict, Any
from ..db.snapshot_repo import write_snapshot_async

logger = logging.getLogger(__name__)


def write_snapshot(turn: int, world_state: Dict[str, Any]) -> None:
    """
    Write world snapshot to PostgreSQL (fire-and-forget).
    
    This function does NOT block the simulation. Errors are logged but not propagated.
    
    Args:
        turn: Current turn number
        world_state: World state dictionary to save
    """
    try:
        write_snapshot_async(turn, world_state)
    except Exception as e:
        # Log error but don't propagate - simulation must continue
        logger.error(f"Error initiating snapshot write for turn {turn}: {e}", exc_info=True)
