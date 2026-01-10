"""Repository for world snapshot persistence."""

import json
import logging
import threading
import queue
from typing import Optional, Dict, Any
from psycopg2 import pool
from .postgres import get_connection, put_connection

logger = logging.getLogger(__name__)

# Queue for snapshot writes (single worker thread processes these)
_snapshot_queue = queue.Queue()
_worker_started = False
_worker_lock = threading.Lock()


def _start_worker():
    """Start the background worker thread if not already started."""
    global _worker_started
    with _worker_lock:
        if not _worker_started:
            _worker_started = True
            worker = threading.Thread(target=_snapshot_worker, daemon=True)
            worker.start()
            logger.debug("Snapshot worker thread started")


def _snapshot_worker():
    """Background worker that processes snapshot writes from queue."""
    while True:
        try:
            item = _snapshot_queue.get(timeout=1.0)
            if item is None:  # Shutdown signal
                break
            
            turn, snapshot = item
            _write_snapshot_sync(turn, snapshot)
            _snapshot_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Error in snapshot worker: {e}", exc_info=True)


def _write_snapshot_sync(turn: int, snapshot: Dict[str, Any]):
    """Synchronously write a snapshot (called by worker thread)."""
    conn = None
    cursor = None
    try:
        # Check if pool is initialized
        from .postgres import _pool
        if _pool is None:
            logger.debug("Database pool not initialized, skipping snapshot write")
            return
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO world_snapshots (turn, snapshot)
            VALUES (%s, %s)
        """, (turn, json.dumps(snapshot)))
        
        conn.commit()
        logger.debug(f"Snapshot written for turn {turn}")
        
    except pool.PoolError as e:
        # Pool exhausted - log but don't crash
        logger.warning(f"Connection pool exhausted, skipping snapshot write for turn {turn}: {e}")
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        # Log error but don't propagate - simulation must continue
        logger.error(f"Error writing snapshot for turn {turn}: {e}", exc_info=True)
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


def write_snapshot_async(turn: int, snapshot: Dict[str, Any]) -> None:
    """
    Write world snapshot to database asynchronously (fire-and-forget).
    
    This function does NOT block the simulation. Errors are logged but not propagated.
    Uses a queue-based system with a single worker thread to prevent connection pool exhaustion.
    
    Args:
        turn: Current turn number
        snapshot: World state dictionary to save
    """
    # Start worker if not already started
    _start_worker()
    
    # Queue the write (non-blocking, will drop if queue is full)
    try:
        _snapshot_queue.put_nowait((turn, snapshot))
    except queue.Full:
        logger.warning(f"Snapshot queue full, dropping write for turn {turn}")


def get_snapshot(turn: int) -> Optional[Dict[str, Any]]:
    """
    Get snapshot for a specific turn.
    
    Args:
        turn: Turn number to retrieve
        
    Returns:
        Snapshot dictionary or None if not found
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT snapshot FROM world_snapshots
            WHERE turn = %s
            ORDER BY id DESC
            LIMIT 1
        """, (turn,))
        
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None
        
    except Exception as e:
        logger.error(f"Error reading snapshot for turn {turn}: {e}")
        return None
    finally:
        if conn:
            cursor.close()
            put_connection(conn)


def get_latest_snapshot() -> Optional[Dict[str, Any]]:
    """
    Get the most recent snapshot.
    
    Returns:
        Snapshot dictionary or None if no snapshots exist
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT snapshot FROM world_snapshots
            ORDER BY turn DESC, id DESC
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None
        
    except Exception as e:
        logger.error(f"Error reading latest snapshot: {e}")
        return None
    finally:
        if conn:
            cursor.close()
            put_connection(conn)
