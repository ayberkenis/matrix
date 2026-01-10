"""Repository for world metrics persistence."""

import logging
import threading
import queue
from typing import Optional, Dict
from decimal import Decimal
from psycopg2 import pool
from .postgres import get_connection, put_connection

logger = logging.getLogger(__name__)

# Queue for metrics writes (single worker thread processes these)
_metrics_queue = queue.Queue()
_worker_started = False
_worker_lock = threading.Lock()


def _start_worker():
    """Start the background worker thread if not already started."""
    global _worker_started
    with _worker_lock:
        if not _worker_started:
            _worker_started = True
            worker = threading.Thread(target=_metrics_worker, daemon=True)
            worker.start()
            logger.debug("Metrics worker thread started")


def _metrics_worker():
    """Background worker that processes metrics writes from queue."""
    while True:
        try:
            item = _metrics_queue.get(timeout=1.0)
            if item is None:  # Shutdown signal
                break
            
            turn, metrics = item
            _write_metrics_sync(turn, metrics)
            _metrics_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Error in metrics worker: {e}", exc_info=True)


def _write_metrics_sync(turn: int, metrics: Dict):
    """Synchronously write metrics (called by worker thread)."""
    conn = None
    cursor = None
    try:
        # Check if pool is initialized
        from .postgres import _pool
        if _pool is None:
            logger.debug("Database pool not initialized, skipping metrics write")
            return
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO world_metrics (
                turn, active_agents, child_pool, total_population,
                tension, food, credits
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (turn) DO UPDATE SET
                active_agents = EXCLUDED.active_agents,
                child_pool = EXCLUDED.child_pool,
                total_population = EXCLUDED.total_population,
                tension = EXCLUDED.tension,
                food = EXCLUDED.food,
                credits = EXCLUDED.credits,
                created_at = NOW()
        """, (
            turn,
            metrics.get("active_agents"),
            metrics.get("child_pool"),
            metrics.get("total_population"),
            metrics.get("tension"),
            metrics.get("food"),
            metrics.get("credits")
        ))
        
        conn.commit()
        logger.debug(f"Metrics written for turn {turn}")
        
    except pool.PoolError as e:
        # Pool exhausted - log but don't crash
        logger.warning(f"Connection pool exhausted, skipping metrics write for turn {turn}: {e}")
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        # Log error but don't propagate - simulation must continue
        logger.error(f"Error writing metrics for turn {turn}: {e}", exc_info=True)
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                put_connection(conn)
            except:
                pass


def write_metrics_async(turn: int, metrics: Dict) -> None:
    """
    Write world metrics to database asynchronously (fire-and-forget).
    
    This function does NOT block the simulation. Errors are logged but not propagated.
    Uses ON CONFLICT to overwrite existing metrics for the same turn.
    Uses a queue-based system with a single worker thread to prevent connection pool exhaustion.
    
    Args:
        turn: Current turn number
        metrics: Dictionary with metrics:
            - active_agents: int
            - child_pool: int
            - total_population: int
            - tension: float
            - food: float
            - credits: float
    """
    # Start worker if not already started
    _start_worker()
    
    # Queue the write (non-blocking, will drop if queue is full)
    try:
        _metrics_queue.put_nowait((turn, metrics))
    except queue.Full:
        logger.warning(f"Metrics queue full, dropping write for turn {turn}")


def get_metrics(turn: int) -> Optional[Dict]:
    """
    Get metrics for a specific turn.
    
    Args:
        turn: Turn number to retrieve
        
    Returns:
        Metrics dictionary or None if not found
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT turn, active_agents, child_pool, total_population,
                   tension, food, credits, created_at
            FROM world_metrics
            WHERE turn = %s
        """, (turn,))
        
        row = cursor.fetchone()
        if row:
            return {
                "turn": row[0],
                "active_agents": row[1],
                "child_pool": row[2],
                "total_population": row[3],
                "tension": float(row[4]) if row[4] is not None else None,
                "food": float(row[5]) if row[5] is not None else None,
                "credits": float(row[6]) if row[6] is not None else None,
                "created_at": row[7].isoformat() if row[7] else None
            }
        return None
        
    except Exception as e:
        logger.error(f"Error reading metrics for turn {turn}: {e}")
        return None
    finally:
        if conn:
            cursor.close()
            put_connection(conn)
