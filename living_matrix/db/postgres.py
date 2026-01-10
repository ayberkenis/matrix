"""PostgreSQL connection pool for Living Matrix."""

import os
import logging
from typing import Optional
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[pool.ThreadedConnectionPool] = None


def get_pool() -> pool.ThreadedConnectionPool:
    """
    Get or create PostgreSQL connection pool.
    
    Reads configuration from environment variables:
    - DB_HOST
    - DB_PORT
    - DB_NAME
    - DB_USER
    - DB_PASSWORD
    
    Raises:
        ValueError: If any required environment variable is missing
    """
    global _pool
    
    if _pool is not None:
        return _pool
    
    # Read required environment variables
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    
    # Validate all required variables are present
    missing = []
    if not db_host:
        missing.append("DB_HOST")
    if not db_port:
        missing.append("DB_PORT")
    if not db_name:
        missing.append("DB_NAME")
    if not db_user:
        missing.append("DB_USER")
    if not db_password:
        missing.append("DB_PASSWORD")
    
    if missing:
        raise ValueError(
            f"Missing required database environment variables: {', '.join(missing)}. "
            "Please set them in .env file."
        )
    
    try:
        port = int(db_port)
    except (ValueError, TypeError):
        raise ValueError(f"DB_PORT must be a valid integer, got: {db_port}")
    
    # Create connection pool
    # Increased maxconn to handle concurrent background writes
    try:
        _pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,  # Increased from 10 to handle more concurrent writes
            host=db_host,
            port=port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        logger.info(f"PostgreSQL connection pool created for {db_user}@{db_host}:{port}/{db_name}")
        return _pool
    except Exception as e:
        logger.error(f"Failed to create PostgreSQL connection pool: {e}")
        raise


def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("PostgreSQL connection pool closed")


def get_connection(timeout=None):
    """
    Get a connection from the pool.
    
    Args:
        timeout: Optional timeout in seconds (not supported by psycopg2 pool, but kept for API compatibility)
    
    Returns:
        psycopg2 connection object
        
    Raises:
        RuntimeError: If pool is not initialized
        pool.PoolError: If pool is exhausted
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call get_pool() first.")
    try:
        return _pool.getconn()
    except pool.PoolError as e:
        logger.warning(f"Connection pool exhausted: {e}")
        raise


def put_connection(conn):
    """Return a connection to the pool."""
    if _pool is not None:
        _pool.putconn(conn)
