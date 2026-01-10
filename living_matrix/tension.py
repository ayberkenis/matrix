"""Multi-dimensional tension system."""

from typing import Dict, Optional
import random

from .dataclasses import Tension
from .constants.tension_constants import (
    DEFAULT_ECONOMIC_TENSION, DEFAULT_SOCIAL_TENSION,
    DEFAULT_POLITICAL_TENSION, DEFAULT_EXISTENTIAL_TENSION,
    TENSION_NORMALIZATION_DIVISOR, DEFAULT_TENSION_DECAY_RATE,
    HIGH_TENSION_THRESHOLD, CRITICAL_TENSION_THRESHOLD
)

# Tension is now imported from dataclasses
# The class definition with methods is in dataclasses/tension_dataclasses.py
