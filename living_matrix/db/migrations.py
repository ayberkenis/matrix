"""Database migrations for Living Matrix."""

import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from .postgres import get_pool, get_connection, put_connection

logger = logging.getLogger(__name__)


def create_tables():
    """
    Create database tables if they don't exist.
    Non-destructive: uses CREATE TABLE IF NOT EXISTS.
    """
    conn = None
    try:
        pool = get_pool()
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create world_snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS world_snapshots (
                id SERIAL PRIMARY KEY,
                turn INTEGER NOT NULL,
                snapshot JSONB NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Create index on turn for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_world_snapshots_turn 
            ON world_snapshots(turn)
        """)
        
        # Create world_metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS world_metrics (
                turn INTEGER PRIMARY KEY,
                active_agents INTEGER,
                child_pool INTEGER,
                total_population INTEGER,
                tension NUMERIC,
                food NUMERIC,
                credits NUMERIC,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        conn.commit()
        logger.info("Database tables created successfully")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error creating database tables: {e}")
        raise
    finally:
        if conn:
            cursor.close()
            put_connection(conn)


def reset_database():
    """
    Reset database by clearing all data from tables.
    WARNING: This deletes all snapshots and metrics!
    """
    conn = None
    try:
        pool = get_pool()
        conn = get_connection()
        cursor = conn.cursor()
        
        # Truncate tables (faster than DELETE, resets auto-increment)
        cursor.execute("TRUNCATE TABLE world_snapshots CASCADE")
        cursor.execute("TRUNCATE TABLE world_metrics CASCADE")
        
        conn.commit()
        logger.info("Database reset: all snapshots and metrics cleared")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error resetting database: {e}")
        raise
    finally:
        if conn:
            cursor.close()
            put_connection(conn)


def initialize_database(fresh: bool = False):
    """
    Initialize database: create pool and tables.
    Should be called once at application startup.
    
    Args:
        fresh: If True, reset database before initializing (clears all data)
    """
    try:
        get_pool()
        if fresh:
            reset_database()
        create_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
