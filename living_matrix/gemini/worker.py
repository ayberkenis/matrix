"""
Async Image Generation Worker for Gemini Visual Intelligence.

This module provides a background worker that:
- Listens for hourly state snapshots
- Calls Gemini with generated prompts
- Stores the latest image with metadata

The worker is:
- Completely decoupled from simulation's advance() method
- Safe to disable entirely
- Running via background thread
- Thread-safe for all operations

IMPORTANT: This worker is OBSERVATIONAL ONLY. It never modifies
simulation state - only reads snapshots and generates images.
"""

import threading
import time
import logging
import hashlib
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import queue

logger = logging.getLogger(__name__)

# Directory for saving generated images
GENERATIONS_DIR = Path(__file__).parent / "generations"
LATEST_IMAGE_PATH = GENERATIONS_DIR / "last.jpg"
LATEST_METADATA_PATH = GENERATIONS_DIR / "last.json"


@dataclass
class GeneratedImage:
    """
    Metadata and data for a generated image.
    
    Stores the latest generated image along with its generation context.
    """
    image_data: bytes  # Raw image bytes
    mime_type: str  # "image/png" or "image/jpeg"
    generated_at_day: int  # Simulation day when generated
    generated_at_hour: int  # Simulation hour when generated
    generated_at_turn: int  # Simulation turn when generated
    generated_at_timestamp: str  # Wall-clock timestamp
    prompt_hash: str  # Hash of the prompt used
    state_hash: str  # Hash of the state snapshot
    generation_time_ms: int  # Time taken to generate
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding binary data)."""
        return {
            "mime_type": self.mime_type,
            "generated_at_day": self.generated_at_day,
            "generated_at_hour": self.generated_at_hour,
            "generated_at_turn": self.generated_at_turn,
            "generated_at_timestamp": self.generated_at_timestamp,
            "prompt_hash": self.prompt_hash,
            "state_hash": self.state_hash,
            "generation_time_ms": self.generation_time_ms,
            "image_size_bytes": len(self.image_data)
        }


class GeminiImageWorker:
    """
    Background worker for Gemini image generation.
    
    Runs in a separate thread and generates images based on
    hourly state snapshots. Only keeps the latest image.
    
    Usage:
        worker = GeminiImageWorker()
        worker.start()
        # ... later, from simulation:
        worker.submit_snapshot(snapshot)
        # ... to get image:
        image = worker.get_latest_image()
        worker.stop()
    
    Thread Safety:
        All public methods are thread-safe.
    
    Rate Limiting:
        - Maximum 1 image per REAL-WORLD hour (wall-clock time)
        - Exponential backoff on rate limit errors (up to 5 min)
        - Skips generation if Gemini quota fails
    """
    
    # Wall-clock rate limiting: 1 image per real-world hour (3600 seconds)
    MIN_SECONDS_BETWEEN_GENERATIONS = 43200  # 12 hours in seconds
    
    # Minimum simulation turn before first image generation (let simulation warm up)
    MIN_TURN_FOR_FIRST_IMAGE = 50
    
    # Backoff settings for rate limit errors
    INITIAL_BACKOFF_SECONDS = 60
    MAX_BACKOFF_SECONDS = 43200  # 12 hours max
    
    def __init__(self):
        """Initialize the worker."""
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Snapshot queue (bounded to prevent memory growth)
        self._snapshot_queue: queue.Queue = queue.Queue(maxsize=5)
        
        # Latest generated image (bounded storage - only keep one)
        self._latest_image: Optional[GeneratedImage] = None
        
        # Wall-clock rate limiting (real-world hours, not simulation)
        self._last_generation_time: float = 0.0  # Unix timestamp of last generation
        self._last_generation_wall_hour: int = -1  # Wall-clock hour (0-23)
        self._current_backoff: float = 0.0  # Current backoff in seconds
        self._rate_limited_until: float = 0.0  # Timestamp when rate limit expires
        
        # Statistics
        self._stats = {
            "images_generated": 0,
            "generation_failures": 0,
            "rate_limit_hits": 0,
            "snapshots_received": 0,
            "snapshots_skipped": 0
        }
        
        # Client and helpers (lazy loaded)
        self._client = None
        self._context_store = None
    
    def start(self) -> None:
        """Start the background worker thread."""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info("Gemini image worker started")
    
    def stop(self) -> None:
        """Stop the background worker gracefully."""
        with self._lock:
            self._running = False
        
        if self._thread:
            # Send sentinel to unblock queue
            try:
                self._snapshot_queue.put(None, timeout=1)
            except queue.Full:
                pass
            
            self._thread.join(timeout=5.0)
            self._thread = None
        
        logger.info("Gemini image worker stopped")
    
    def submit_snapshot(self, snapshot) -> bool:
        """
        Submit a state snapshot for image generation.
        
        This method is non-blocking and thread-safe.
        If the queue is full, the snapshot is dropped.
        
        Args:
            snapshot: StateSnapshot to process
        
        Returns:
            True if snapshot was queued, False if dropped
        """
        with self._lock:
            self._stats["snapshots_received"] += 1
        
        try:
            self._snapshot_queue.put_nowait(snapshot)
            return True
        except queue.Full:
            with self._lock:
                self._stats["snapshots_skipped"] += 1
            return False
    
    def get_latest_image(self) -> Optional[GeneratedImage]:
        """
        Get the latest generated image.
        
        Thread-safe. Returns image from memory if available,
        otherwise tries to load from disk.
        """
        with self._lock:
            if self._latest_image is not None:
                return self._latest_image
        
        # Try to load from disk if not in memory
        disk_image = self.load_image_from_disk()
        if disk_image:
            with self._lock:
                self._latest_image = disk_image
            return disk_image
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        current_time = time.time()
        current_wall_hour = datetime.now().hour
        
        with self._lock:
            stats = self._stats.copy()
            stats["has_image"] = self._latest_image is not None
            stats["running"] = self._running
            stats["current_backoff"] = self._current_backoff
            stats["current_wall_hour"] = current_wall_hour
            stats["last_generation_wall_hour"] = self._last_generation_wall_hour
            
            # Time until next generation allowed
            time_since_last = current_time - self._last_generation_time
            if time_since_last < self.MIN_SECONDS_BETWEEN_GENERATIONS:
                stats["next_generation_in_seconds"] = int(self.MIN_SECONDS_BETWEEN_GENERATIONS - time_since_last)
            else:
                stats["next_generation_in_seconds"] = 0
            
            # Rate limit status (from API)
            if current_time < self._rate_limited_until:
                stats["rate_limited"] = True
                stats["rate_limit_remaining_seconds"] = int(self._rate_limited_until - current_time)
            else:
                stats["rate_limited"] = False
                stats["rate_limit_remaining_seconds"] = 0
            
            if self._latest_image:
                stats["latest_image_day"] = self._latest_image.generated_at_day
                stats["latest_image_hour"] = self._latest_image.generated_at_hour
                stats["latest_image_timestamp"] = self._latest_image.generated_at_timestamp
            return stats
    
    def is_running(self) -> bool:
        """Check if worker is running."""
        with self._lock:
            return self._running
    
    def _run_loop(self) -> None:
        """Main worker loop (runs in background thread)."""
        logger.debug("Gemini worker loop started")
        
        while True:
            with self._lock:
                if not self._running:
                    break
            
            try:
                # Wait for snapshot with timeout
                snapshot = self._snapshot_queue.get(timeout=1.0)
                
                if snapshot is None:
                    # Sentinel received, exit
                    break
                
                self._process_snapshot(snapshot)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in Gemini worker loop: {e}", exc_info=True)
        
        logger.debug("Gemini worker loop ended")
    
    def _process_snapshot(self, snapshot) -> None:
        """Process a single snapshot."""
        # Rate limit check
        should_gen, reason = self._should_generate_with_reason(snapshot)
        if not should_gen:
            # Only log occasionally to avoid spam
            with self._lock:
                received = self._stats.get("snapshots_received", 0)
            if received % 10 == 1:  # Log every 10th snapshot
                print(f"[GEMINI WORKER] Skipping generation: {reason}")
            return
        
        # Lazy load client
        if self._client is None:
            from .client import get_client
            self._client = get_client()
        
        if not self._client.is_available:
            print("[GEMINI WORKER] Client not available - check GEMINI_API_KEY")
            return
        
        # Lazy load context store
        if self._context_store is None:
            from .context_store import get_context_store
            self._context_store = get_context_store()
        
        # Add snapshot to context store for daily summaries
        self._context_store.add_hourly_snapshot(snapshot)
        
        print(f"[GEMINI WORKER] Starting image generation (wall hour: {datetime.now().hour}, model: {self._client.IMAGE_MODEL})")
        
        try:
            self._generate_image(snapshot)
        except Exception as e:
            print(f"[GEMINI WORKER] Image generation failed: {e}")
            with self._lock:
                self._stats["generation_failures"] += 1
    
    def _should_generate(self, snapshot) -> bool:
        """Check if we should generate an image for this snapshot."""
        should_gen, _ = self._should_generate_with_reason(snapshot)
        return should_gen
    
    def _should_generate_with_reason(self, snapshot) -> tuple:
        """
        Check if we should generate an image for this snapshot.
        
        Rate limiting based on REAL-WORLD time (wall-clock), not simulation time:
        1. Wait until simulation reaches MIN_TURN_FOR_FIRST_IMAGE (warmup)
        2. Max 1 image per MIN_SECONDS_BETWEEN_GENERATIONS
        3. Exponential backoff on rate limit errors
        
        This means images are generated every actual hour regardless of
        how fast the simulation is running.
        
        Returns:
            Tuple of (should_generate: bool, reason: str)
        """
        current_time = time.time()
        
        # Check if simulation has warmed up (wait for turn 50)
        if snapshot.simulation_turn < self.MIN_TURN_FOR_FIRST_IMAGE:
            remaining = self.MIN_TURN_FOR_FIRST_IMAGE - snapshot.simulation_turn
            return False, f"Waiting for simulation warmup (turn {snapshot.simulation_turn}/{self.MIN_TURN_FOR_FIRST_IMAGE}, {remaining} turns remaining)"
        
        with self._lock:
            # Check rate limit backoff first (from API rate limits)
            if current_time < self._rate_limited_until:
                wait_time = int(self._rate_limited_until - current_time)
                return False, f"API rate limited, waiting {wait_time}s more"
            
            # Check minimum time between generations
            time_since_last = current_time - self._last_generation_time
            if self._last_generation_time > 0 and time_since_last < self.MIN_SECONDS_BETWEEN_GENERATIONS:
                remaining = int(self.MIN_SECONDS_BETWEEN_GENERATIONS - time_since_last)
                return False, f"Too soon since last generation, waiting {remaining}s more"
            
            # All checks passed - generate!
            return True, "Ready to generate"
    
    def _generate_image(self, snapshot) -> None:
        """Generate an image from the snapshot."""
        from .prompt_builder import build_image_prompt, get_system_prompt
        from .client import GeminiError
        
        # Build prompt
        prompt = build_image_prompt(snapshot)
        system_prompt = get_system_prompt()
        
        # Add context if available
        if self._context_store:
            context = self._context_store.get_context_for_prompt()
            if context:
                prompt = f"{context}\n\n{prompt}"
        
        # Calculate hashes
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:12]
        state_hash = snapshot.compute_hash()
        
        logger.info(f"Generating Matrix image for Day {snapshot.simulation_day} Hour {snapshot.simulation_hour}")
        
        # Record API call time BEFORE making the call
        with self._lock:
            self._last_api_call_time = time.time()
        
        try:
            # Call Gemini
            result = self._client.generate_image(
                prompt=prompt,
                system_prompt=system_prompt
            )
        except GeminiError as e:
            # Handle rate limit with exponential backoff
            if e.status_code == 429 or "rate limit" in str(e).lower():
                self._handle_rate_limit()
            raise
        
        if result is None:
            logger.warning("Gemini returned no image")
            with self._lock:
                self._stats["generation_failures"] += 1
            return
        
        # Success - reset backoff
        with self._lock:
            self._current_backoff = 0.0
        
        # Create image record
        image = GeneratedImage(
            image_data=result.image_data,
            mime_type=result.mime_type,
            generated_at_day=snapshot.simulation_day,
            generated_at_hour=snapshot.simulation_hour,
            generated_at_turn=snapshot.simulation_turn,
            generated_at_timestamp=datetime.now().isoformat(),
            prompt_hash=prompt_hash,
            state_hash=state_hash,
            generation_time_ms=result.generation_time_ms
        )
        
        # Store image (only keep latest)
        with self._lock:
            self._latest_image = image
            self._last_generation_time = time.time()
            self._last_generation_wall_hour = datetime.now().hour
            self._stats["images_generated"] += 1
        
        # Save to disk
        self._save_image_to_disk(image)
        
        print(
            f"[GEMINI WORKER] ✓ Image generated successfully: {len(result.image_data)} bytes, "
            f"{result.generation_time_ms}ms, saved for Day {snapshot.simulation_day}"
        )
    
    def _handle_rate_limit(self) -> None:
        """Handle rate limit by setting exponential backoff."""
        with self._lock:
            self._stats["rate_limit_hits"] += 1
            
            # Calculate backoff with exponential increase
            if self._current_backoff == 0:
                self._current_backoff = self.INITIAL_BACKOFF_SECONDS
            else:
                self._current_backoff = min(
                    self._current_backoff * 2,
                    self.MAX_BACKOFF_SECONDS
                )
            
            self._rate_limited_until = time.time() + self._current_backoff
            
            logger.warning(
                f"Rate limited by Gemini API. Backing off for {self._current_backoff}s "
                f"(rate_limit_hits: {self._stats['rate_limit_hits']})"
            )
    
    def _save_image_to_disk(self, image: GeneratedImage) -> bool:
        """
        Save generated image to disk for API serving.
        
        Saves to gemini/generations/last.jpg and last.json
        
        Args:
            image: GeneratedImage to save
            
        Returns:
            True if saved successfully
        """
        try:
            # Ensure directory exists
            GENERATIONS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Save image file
            with open(LATEST_IMAGE_PATH, 'wb') as f:
                f.write(image.image_data)
            
            # Save metadata
            metadata = image.to_dict()
            with open(LATEST_METADATA_PATH, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved image to {LATEST_IMAGE_PATH} ({len(image.image_data)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save image to disk: {e}")
            return False
    
    @staticmethod
    def load_image_from_disk() -> Optional['GeneratedImage']:
        """
        Load the latest image from disk.
        
        Returns:
            GeneratedImage or None if not found
        """
        try:
            if not LATEST_IMAGE_PATH.exists() or not LATEST_METADATA_PATH.exists():
                return None
            
            # Load image data
            with open(LATEST_IMAGE_PATH, 'rb') as f:
                image_data = f.read()
            
            # Load metadata
            with open(LATEST_METADATA_PATH, 'r') as f:
                metadata = json.load(f)
            
            return GeneratedImage(
                image_data=image_data,
                mime_type=metadata.get('mime_type', 'image/jpeg'),
                generated_at_day=metadata.get('generated_at_day', 0),
                generated_at_hour=metadata.get('generated_at_hour', 0),
                generated_at_turn=metadata.get('generated_at_turn', 0),
                generated_at_timestamp=metadata.get('generated_at_timestamp', ''),
                prompt_hash=metadata.get('prompt_hash', ''),
                state_hash=metadata.get('state_hash', ''),
                generation_time_ms=metadata.get('generation_time_ms', 0)
            )
            
        except Exception as e:
            logger.error(f"Failed to load image from disk: {e}")
            return None
    
    @staticmethod
    def get_image_path() -> Path:
        """Get the path to the latest image file."""
        return LATEST_IMAGE_PATH
    
    @staticmethod
    def get_metadata_path() -> Path:
        """Get the path to the latest metadata file."""
        return LATEST_METADATA_PATH


# Singleton worker instance
_worker: Optional[GeminiImageWorker] = None


def get_worker() -> GeminiImageWorker:
    """Get the singleton worker instance."""
    global _worker
    if _worker is None:
        _worker = GeminiImageWorker()
    return _worker


def start_worker() -> GeminiImageWorker:
    """Get and start the singleton worker."""
    worker = get_worker()
    worker.start()
    return worker


def stop_worker() -> None:
    """Stop the singleton worker if running."""
    global _worker
    if _worker is not None:
        _worker.stop()
