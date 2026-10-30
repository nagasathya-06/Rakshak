"""
Project Rakshak - Global Configuration & Simulation Constants
Aligned with SDG 11: Sustainable Cities and Communities
"""

from pydantic import BaseModel
from typing import List, Dict, Any


class GridConfig(BaseModel):
    # Nominal Grid Parameters
    f0: float = 50.0                # Nominal frequency (Hz)
    H: float = 5.0                  # Grid inertia constant (seconds)
    D: float = 1.0                  # Load damping factor
    governor_droop: float = 0.05    # Governor speed regulation (5%)
    governor_time_constant: float = 0.5  # Governor valve lag (s)
    f_collapse: float = 47.5        # Frequency at which power plants trip (cascading blackout)

    # Protection & Shedding Thresholds
    threshold_smart_shed: float = 49.60   # Rakshak primary shedding threshold (Hz)
    threshold_rocof_severe: float = -0.50 # RoCoF (Hz/s) for predictive early trip
    threshold_recover: float = 49.90      # Grid frequency considered recovered (Hz)
    hysteresis_band: float = 0.15         # Frequency hysteresis to prevent relay chattering (Hz)

    # UFLS (Under-Frequency Load Shedding) Feeder Stages
    ufls_stages: List[float] = [49.2, 49.0, 48.8, 48.6]

    # Staggered Restoration Parameters
    restore_spread: float = 40.0   # Max delay spread (seconds) for randomized MAC hashing
    compressor_lockout: float = 15.0 # Minimum cooldown time (seconds in sim scale) before AC can restart


# Appliance Definitions for 3-Tier Priority Matrix
APPLIANCE_CATALOG: Dict[str, Dict[str, Any]] = {
    "fridge": {
        "name": "Refrigerator",
        "power_w": 150.0,
        "tier": 0,           # CRITICAL (Tier 0)
        "inrush_ratio": 2.5,
        "tau_inrush": 10.0,
        "is_compressor": True,
        "lockout_s": 12.0
    },
    "lights": {
        "name": "LED Lighting",
        "power_w": 100.0,
        "tier": 0,           # CRITICAL (Tier 0)
        "inrush_ratio": 1.0,
        "tau_inrush": 0.1,
        "is_compressor": False,
        "lockout_s": 0.0
    },
    "o2": {
        "name": "Oxygen Concentrator / Medical",
        "power_w": 300.0,
        "tier": 0,           # CRITICAL (Tier 0)
        "inrush_ratio": 1.0,
        "tau_inrush": 0.5,
        "is_compressor": False,
        "lockout_s": 0.0
    },
    "fan": {
        "name": "Ceiling Fan / Ventilation",
        "power_w": 75.0,
        "tier": 1,           # ESSENTIAL (Tier 1)
        "inrush_ratio": 1.4,
        "tau_inrush": 5.0,
        "is_compressor": False,
        "lockout_s": 0.0
    },
    "ac": {
        "name": "Air Conditioner",
        "power_w": 1500.0,
        "tier": 2,           # DEFERRABLE (Tier 2)
        "inrush_ratio": 3.0,
        "tau_inrush": 15.0,
        "is_compressor": True,
        "lockout_s": 15.0
    },
    "heater": {
        "name": "Water Heater / Geyser",
        "power_w": 2000.0,
        "tier": 2,           # DEFERRABLE (Tier 2)
        "inrush_ratio": 1.1,
        "tau_inrush": 2.0,
        "is_compressor": False,
        "lockout_s": 0.0
    },
    "ev": {
        "name": "EV Fast Charger",
        "power_w": 3300.0,
        "tier": 2,           # DEFERRABLE (Tier 2)
        "inrush_ratio": 1.0,
        "tau_inrush": 1.0,
        "is_compressor": False,
        "lockout_s": 0.0
    }
}

TIER_NAMES = {
    0: "CRITICAL",
    1: "ESSENTIAL",
    2: "DEFERRABLE"
}

TIER_COLORS = {
    0: "#22c55e",  # Green
    1: "#3b82f6",  # Blue
    2: "#f97316"   # Orange
}
