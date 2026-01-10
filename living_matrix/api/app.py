"""FastAPI application for Living Matrix."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from living_matrix.core.runner import WorldRunner
from living_matrix.core.ipc import MatrixStateStore, MatrixCommandQueue
from living_matrix.api.routes import setup_routes, set_dependencies
from living_matrix.api.ws import websocket_endpoint
from living_matrix.version import VersionManager

# Global instances (initialized in lifespan)
state_store: MatrixStateStore = None
command_queue: MatrixCommandQueue = None
world_runner: WorldRunner = None
version_manager: VersionManager = None

# Debug mode - enable control endpoints (pause, resume, speed)
# Set via environment variable MATRIX_DEBUG=true or MATRIX_DEBUG=1
MATRIX_DEBUG = os.getenv("MATRIX_DEBUG", "false").lower() in ("true", "1", "yes", "on")


@asynccontextmanager
async def lifespan(app: FastAPI, fresh: bool = False):
    """Lifespan context manager for startup/shutdown."""
    global state_store, command_queue, world_runner, version_manager
    
    # Startup: Initialize and start world runner
    # Import Simulation from core.py (parent directory)
    import sys
    from pathlib import Path
    parent_dir = Path(__file__).parent.parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    # Import Simulation class from core.py
    import importlib.util
    core_path = parent_dir / "living_matrix" / "core.py"
    spec = importlib.util.spec_from_file_location("living_matrix.core_module", core_path)
    core_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core_module)
    Simulation = core_module.Simulation
    
    # Initialize version manager
    version_manager = VersionManager(data_dir="data")
    version_manager.load()  # Load or create version data
    
    simulation = Simulation(data_dir="data", autopilot_enabled=True, fresh=fresh)
    state_store = MatrixStateStore()
    command_queue = MatrixCommandQueue()
    world_runner = WorldRunner(simulation, state_store, command_queue, version_manager)
    
    # Start background runner
    world_runner.start()
    
    # Set dependencies for routes and WebSocket
    set_dependencies(state_store, command_queue, version_manager)
    from living_matrix.api.ws import set_state_store as set_ws_state_store
    set_ws_state_store(state_store)
    
    print("Living Matrix background runner started")
    
    yield
    
    # Shutdown: Stop world runner gracefully
    if world_runner:
        world_runner.stop()
        print("Living Matrix background runner stopped")


def create_app(fresh: bool = False) -> FastAPI:
    """Create and configure FastAPI application.
    
    Args:
        fresh: If True, reset database before starting (clears all snapshots and metrics)
    """
    # Create a closure to pass fresh flag to lifespan
    @asynccontextmanager
    async def lifespan_with_fresh(app: FastAPI):
        async with lifespan(app, fresh=fresh):
            yield
    
    app = FastAPI(
        title="Living Matrix API",
        description="REST API and WebSocket for Living Matrix simulation",
        version="1.0.0",
        lifespan=lifespan_with_fresh
    )
    
    # CORS middleware (allow all origins for development)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Setup routes (will use globals set in lifespan)
    router = setup_routes(debug_mode=MATRIX_DEBUG)
    app.include_router(router)
    
    # Log debug mode status
    if MATRIX_DEBUG:
        print("⚠️  MATRIX_DEBUG enabled - Control endpoints (pause/resume/speed) are available")
    else:
        print("ℹ️  MATRIX_DEBUG disabled - Control endpoints are hidden")
    
    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_route(websocket: WebSocket):
        await websocket_endpoint(websocket)
    
    return app
