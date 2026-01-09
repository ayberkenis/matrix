"""Core simulation modules."""

# Import Simulation from parent core.py
# Use importlib to avoid circular imports
import sys
from pathlib import Path

# Add parent to path and import
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import Simulation class from core.py
# We'll import it dynamically to avoid circular dependency
def get_simulation_class():
    """Get Simulation class from core.py."""
    import importlib.util
    core_path = parent_dir / "core.py"
    spec = importlib.util.spec_from_file_location("living_matrix.core_module", core_path)
    core_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core_module)
    return core_module.Simulation

# Lazy import - will be loaded when needed
Simulation = None

def _get_simulation():
    """Lazy getter for Simulation class."""
    global Simulation
    if Simulation is None:
        Simulation = get_simulation_class()
    return Simulation

# Make it importable
__all__ = ['Simulation', '_get_simulation']
