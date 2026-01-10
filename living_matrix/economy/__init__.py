"""Economy system modules."""

from .food_system import *
from .credit_system import *
from .tension_system import *
from .economy_utils import *

# Import EconomySystem from the parent economy.py file
# This handles the case where both economy.py and economy/ exist
import sys
import importlib.util
from pathlib import Path

parent_dir = Path(__file__).parent.parent
economy_file = parent_dir / "economy.py"

if economy_file.exists():
    spec = importlib.util.spec_from_file_location("living_matrix.economy_file", economy_file)
    if spec and spec.loader:
        economy_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(economy_module)
        EconomySystem = economy_module.EconomySystem
        DistrictEconomy = economy_module.DistrictEconomy
