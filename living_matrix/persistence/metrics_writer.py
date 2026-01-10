"""Metrics writer for world metrics persistence."""

import logging
from typing import Dict, Optional
from ..db.metrics_repo import write_metrics_async

logger = logging.getLogger(__name__)


def write_metrics(turn: int, metrics: Dict) -> None:
    """
    Write world metrics to PostgreSQL (fire-and-forget).
    
    This function does NOT block the simulation. Errors are logged but not propagated.
    
    Args:
        turn: Current turn number
        metrics: Dictionary with metrics:
            - active_agents: int (optional)
            - child_pool: int (optional)
            - total_population: int (optional)
            - tension: float (optional)
            - food: float (optional)
            - credits: float (optional)
    """
    try:
        write_metrics_async(turn, metrics)
    except Exception as e:
        # Log error but don't propagate - simulation must continue
        logger.error(f"Error initiating metrics write for turn {turn}: {e}", exc_info=True)
