"""
Project Rakshak - Multi-Building Fleet & Distribution Feeder Simulator
Implements:
1. Micro-view: 12 detailed buildings (Houses, Medical Clinic, Shops, Apartment Block)
2. Macro-feeder view: 500 heterogeneous virtual buildings (Oyefeso et al., IEEE 2024)
3. Physical AC Compressor Lockout protection against short-cycling
4. Decentralized MAC-Address Hash Staggered Restoration
"""

import math
import hashlib
from typing import List, Dict, Any, Optional
from config import GridConfig, APPLIANCE_CATALOG, TIER_NAMES


def pseudo_hash_mac(mac: str, salt: str = "rakshak") -> float:
    """
    Simulates hardware MAC address hashing on microcontrollers:
    Hash(MAC || DeviceKey) maps deterministically to uniform [0.0, 1.0].
    """
    key = f"{mac}:{salt}".encode("utf-8")
    digest = hashlib.md5(key).hexdigest()
    int_val = int(digest[:8], 16)
    return (int_val % 10000) / 10000.0


class SimulatedDevice:
    def __init__(self, key: str, multiplier: float = 1.0, has_device: bool = True, user_wants: bool = True):
        spec = APPLIANCE_CATALOG[key]
        self.key = key
        self.name = spec["name"]
        self.base_w = spec["power_w"] * multiplier
        self.tier = spec["tier"]
        self.inrush_ratio = spec["inrush_ratio"]
        self.tau = spec["tau_inrush"]
        self.is_compressor = spec["is_compressor"]
        self.lockout_duration = spec["lockout_s"]

        self.has_device = has_device
        self.user_wants = user_wants
        self.is_on = True
        self.t_on = -1000.0
        self.t_off = -1000.0

    def turn_off(self, current_t: float):
        if self.is_on:
            self.is_on = False
            self.t_off = current_t

    def can_turn_on(self, current_t: float) -> bool:
        """Enforces compressor lockout period (Oyefeso et al., IEEE 2024)."""
        if self.is_compressor:
            if (current_t - self.t_off) < self.lockout_duration:
                return False
        return True

    def turn_on(self, current_t: float) -> bool:
        if not self.can_turn_on(current_t):
            return False
        self.is_on = True
        self.t_on = current_t
        return True

    def get_power_w(self, current_t: float) -> float:
        if not (self.has_device and self.user_wants and self.is_on):
            return 0.0
        # Inrush transient decay: P(t) = P_steady * (1 + (inrush - 1) * exp(-(t - t_on)/tau))
        inrush_factor = 1.0 + (self.inrush_ratio - 1.0) * math.exp(-max(0.0, current_t - self.t_on) / max(0.1, self.tau))
        return self.base_w * inrush_factor


class BuildingAgent:
    def __init__(self, idx: int, b_type: str, feeder_idx: int, is_medical: bool = False, mult: float = 1.0):
        self.idx = idx
        self.b_type = b_type
        self.feeder_idx = feeder_idx
        self.is_medical = is_medical
        self.mult = mult
        self.mac = f"A4:CF:12:{((idx * 37 + 11) & 0xFF):02X}:{((idx * 91 + 7) & 0xFF):02X}:{((idx * 53 + 3) & 0xFF):02X}"
        self.energized = True       # Feeder power status
        self.local_freq_offset = (math.sin(idx * 1.7) * 0.015) # Small sensor noise/offset
        self.devices: Dict[str, SimulatedDevice] = {}
        self.stagger_timers: Dict[str, float] = {}
        self.stagger_delays: Dict[str, float] = {}

        self._init_devices()

    def _init_devices(self):
        # Base ownership
        for k in ["fridge", "lights", "fan"]:
            self.devices[k] = SimulatedDevice(k, multiplier=self.mult, has_device=True, user_wants=True)

        # Medical device (always on in clinics, or randomly in select houses)
        has_o2 = self.is_medical
        self.devices["o2"] = SimulatedDevice("o2", multiplier=self.mult, has_device=has_o2, user_wants=has_o2)

        # Deferrable loads
        has_ac = (self.b_type != "shop") or (self.idx % 2 == 0)
        has_heater = (self.b_type == "house" and self.idx % 2 == 1) or (self.b_type == "apartment")
        has_ev = (self.b_type == "house" and self.idx % 3 == 0) or (self.b_type == "apartment")

        self.devices["ac"] = SimulatedDevice("ac", multiplier=self.mult, has_device=has_ac, user_wants=has_ac)
        self.devices["heater"] = SimulatedDevice("heater", multiplier=self.mult, has_device=has_heater, user_wants=has_heater)
        self.devices["ev"] = SimulatedDevice("ev", multiplier=self.mult, has_device=has_ev, user_wants=has_ev)

        for k in self.devices.keys():
            self.stagger_timers[k] = 0.0
            self.stagger_delays[k] = 0.0

    def step_agent(self, current_t: float, dt: float, grid_freq: float, rocof: float, mode: str, cfg: GridConfig):
        if not self.energized:
            return

        local_f = grid_freq + self.local_freq_offset

        # Mode: Smart Rakshak (with or without staggered restoration)
        if mode in ["rakshak", "rakshak_unstaggered"]:
            is_staggered = (mode == "rakshak")
            # RoCoF early predictive trigger for Tier 2 deferrable loads
            severe_rocof = (rocof <= cfg.threshold_rocof_severe)

            for key, dev in self.devices.items():
                if dev.tier == 0:
                    continue  # CRITICAL LOADS ARE NEVER SHED

                # Tier 2 (Deferrable: AC, Heater, EV) and Tier 1 (Essential: Fan)
                trip_threshold = cfg.threshold_smart_shed if dev.tier == 2 else (cfg.threshold_smart_shed - 0.40)

                # Shedding Condition
                if dev.is_on:
                    should_shed = (local_f <= trip_threshold) or (severe_rocof and local_f < 49.80 and dev.tier == 2)
                    if should_shed:
                        dev.turn_off(current_t)
                        self.stagger_timers[key] = 0.0
                        if is_staggered:
                            # Deterministic decentralized hash delay
                            h = pseudo_hash_mac(self.mac, salt=key)
                            self.stagger_delays[key] = 2.0 + (h * cfg.restore_spread)
                        else:
                            self.stagger_delays[key] = 0.0

                # Restoration Condition (Grid frequency recovered past hysteresis band)
                else:
                    if local_f >= (trip_threshold + cfg.hysteresis_band):
                        self.stagger_timers[key] += dt
                        if self.stagger_timers[key] >= self.stagger_delays[key]:
                            # Attempt turn-on (respects compressor lockout)
                            dev.turn_on(current_t)

    def get_total_power_w(self, current_t: float) -> float:
        if not self.energized:
            return 0.0
        return sum(dev.get_power_w(current_t) for dev in self.devices.values())


class FleetSimulator:
    def __init__(self, config: Optional[GridConfig] = None):
        self.cfg = config or GridConfig()
        self.micro_buildings: List[BuildingAgent] = []
        self.macro_fleet: List[BuildingAgent] = []
        self.ufls_feeder_tripped = [False, False, False, False]
        self.ufls_stage_timers = [0.0, 0.0, 0.0, 0.0]
        self.init_fleet()

    def init_fleet(self):
        """Construct the 12 micro-buildings and 500 macro-feeder virtual buildings."""
        self.micro_buildings.clear()
        building_types = ["house", "house", "clinic", "house", "shop", "house", 
                          "house", "apartment", "house", "house", "house", "house"]
        multipliers = {"house": 1.0, "clinic": 2.5, "shop": 1.5, "apartment": 4.0}

        # 12 Micro-View Buildings (Matching 3D scene)
        for i, b_type in enumerate(building_types):
            is_med = (b_type == "clinic") or (i in [1, 3, 7, 9])
            feeder = i // 3
            mult = multipliers[b_type]
            agent = BuildingAgent(idx=i, b_type=b_type, feeder_idx=feeder, is_medical=is_med, mult=mult)
            self.micro_buildings.append(agent)

        # Baseline total power of micro-buildings
        self.baseline_micro_w = sum(b.get_total_power_w(0.0) for b in self.micro_buildings)

        # Macro Fleet: 500 heterogeneous buildings
        self.macro_fleet.clear()
        for i in range(500):
            b_type = "apartment" if (i % 20 == 0) else ("clinic" if (i % 50 == 0) else "house")
            is_med = (b_type == "clinic") or (i % 8 == 0)
            feeder = i % 4
            mult = 3.0 if b_type == "apartment" else (2.0 if b_type == "clinic" else 1.0)
            self.macro_fleet.append(BuildingAgent(idx=i + 100, b_type=b_type, feeder_idx=feeder, is_medical=is_med, mult=mult))

        self.baseline_macro_w = sum(b.get_total_power_w(0.0) for b in self.macro_fleet)

    def step(self, current_t: float, dt: float, grid_freq: float, rocof: float, mode: str) -> float:
        """
        Advance all buildings and return normalized total active load (p.u.).
        """
        # 1. Conventional UFLS Feeder Breaker Logic
        if mode == "ufls":
            self._step_ufls(current_t, dt, grid_freq)

        # 2. Advance all individual micro building agents
        for b in self.micro_buildings:
            b.step_agent(current_t, dt, grid_freq, rocof, mode, self.cfg)

        # 3. Advance macro fleet
        for b in self.macro_fleet:
            b.step_agent(current_t, dt, grid_freq, rocof, mode, self.cfg)

        # Aggregate total micro power
        total_w = sum(b.get_total_power_w(current_t) for b in self.micro_buildings)
        return total_w / max(1.0, self.baseline_micro_w)

    def _step_ufls(self, current_t: float, dt: float, grid_freq: float):
        """Standard 4-stage feeder shedding by substation circuit breakers."""
        stages = self.cfg.ufls_stages
        feeder_order = [0, 2, 1, 3]

        for stage_idx in range(4):
            if not self.ufls_feeder_tripped[feeder_order[stage_idx]]:
                if grid_freq <= stages[stage_idx]:
                    self.ufls_stage_timers[stage_idx] += dt
                    if self.ufls_stage_timers[stage_idx] >= 0.10: # 100ms breaker trip delay
                        feeder = feeder_order[stage_idx]
                        self.ufls_feeder_tripped[feeder] = True
                        for b in self.micro_buildings:
                            if b.feeder_idx == feeder:
                                b.energized = False
                        for b in self.macro_fleet:
                            if b.feeder_idx == feeder:
                                b.energized = False
                else:
                    self.ufls_stage_timers[stage_idx] = 0.0

        # Restoration: Bulk simultaneous reconnection once grid reaches 49.95 Hz for 10s
        if grid_freq >= 49.90 and any(self.ufls_feeder_tripped):
            if current_t > 70.0:
                self.ufls_feeder_tripped = [False, False, False, False]
                for b in self.micro_buildings:
                    b.energized = True
                for b in self.macro_fleet:
                    b.energized = True
