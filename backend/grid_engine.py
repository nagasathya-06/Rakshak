"""
Project Rakshak - Grid Physics & Swing Equation Engine
Solves the differential equations governing grid frequency dynamics,
inertia response, turbine governor action, and generation-demand balance.
"""

import math
from typing import List, Tuple, Dict, Any, Optional
from config import GridConfig


class GridEngine:
    def __init__(self, config: Optional[GridConfig] = None):
        self.cfg = config or GridConfig()
        self.reset()

    def reset(self, loss: float = 0.18, t_trip: float = 5.0, t_rec: float = 45.0, ramp: float = 30.0):
        """Reset the grid state variables."""
        self.t = 0.0
        self.dt = 0.05
        self.x = 0.0              # Fractional frequency deviation: (f - f0) / f0
        self.f = self.cfg.f0      # Current frequency in Hz
        self.pg = 0.0             # Governor active power adjustment
        self.loss = loss          # Magnitude of generation lost (e.g., 0.18 for 18%)
        self.t_trip = t_trip      # Timestamp of generation trip
        self.t_rec = t_rec        # Timestamp when lost generation begins ramp return
        self.ramp = ramp          # Duration of generation ramp recovery (seconds)
        self.collapsed = False

        # History buffers for telemetry and derivative calculations
        self.history_t: List[float] = [0.0]
        self.history_f: List[float] = [self.cfg.f0]
        self.history_pl: List[float] = [1.0]

        # Performance Metrics
        self.nadir = self.cfg.f0
        self.max_rocof = 0.0
        self.recovery_time: Optional[float] = None
        self.blackout_events = 0
        self.critical_energy_not_served_wh = 0.0
        self.medical_minutes_lost = 0.0
        self.post_shed_peak_load = 0.0

    def compute_rocof(self, window_points: int = 5) -> float:
        """
        Calculate Rate of Change of Frequency (RoCoF = df/dt in Hz/s)
        over a short trailing sliding window.
        """
        n = len(self.history_f)
        if n < 2:
            return 0.0
        window = min(window_points, n)
        delta_f = self.history_f[-1] - self.history_f[-window]
        delta_t = (window - 1) * self.dt
        if delta_t <= 0:
            return 0.0
        return delta_f / delta_t

    def get_generation_supply(self, current_t: float) -> float:
        """
        Calculate scheduled generation supply (p.u.) based on
        pre-trip, post-trip, and ramp-recovery timeline.
        """
        if current_t < self.t_trip:
            return 1.0
        elif current_t < self.t_rec:
            return 1.0 - self.loss
        else:
            fraction_recovered = min(1.0, (current_t - self.t_rec) / self.ramp)
            return (1.0 - self.loss) + (self.loss * fraction_recovered)

    def step(self, total_load_pu: float) -> Dict[str, Any]:
        """
        Advance grid simulation by 1 time step dt (50ms) using the Swing Equation:
        2H * d(x)/dt = P_mech + P_gov - P_load - D * x
        where x = (f - f0) / f0.
        """
        if self.collapsed:
            self.f = 47.5
            self.history_f.append(self.f)
            self.history_t.append(self.t)
            self.history_pl.append(total_load_pu)
            self.t += self.dt
            return self.get_state(total_load_pu)

        p_scheduled = self.get_generation_supply(self.t)

        # Primary frequency control (Turbine Governor droop response)
        # Target governor effort: inversely proportional to frequency deviation
        target_gov = max(-0.30, min(0.15, -self.x / self.cfg.governor_droop))
        self.pg += (target_gov - self.pg) * (self.dt / self.cfg.governor_time_constant)

        # Swing Equation numerical integration
        dx_dt = (p_scheduled + self.pg - total_load_pu - self.cfg.D * self.x) / (2.0 * self.cfg.H)
        self.x += dx_dt * self.dt

        # Instantaneous frequency
        self.f = self.cfg.f0 * (1.0 + self.x)

        # Check cascading collapse threshold
        if self.f <= self.cfg.f_collapse:
            self.collapsed = True
            self.f = self.cfg.f_collapse
            self.x = (self.cfg.f_collapse - self.cfg.f0) / self.cfg.f0

        # Update metrics once trip occurs
        if self.t >= self.t_trip:
            if self.f < self.nadir:
                self.nadir = self.f
                self.recovery_time = None

            if self.recovery_time is None and self.nadir < self.cfg.threshold_recover and self.f >= self.cfg.threshold_recover:
                self.recovery_time = self.t - self.t_trip

            current_rocof = abs(self.compute_rocof(window_points=5))
            if current_rocof > self.max_rocof:
                self.max_rocof = current_rocof

        self.history_f.append(self.f)
        self.history_t.append(self.t)
        self.history_pl.append(total_load_pu)
        self.t += self.dt

        return self.get_state(total_load_pu)

    def get_state(self, total_load_pu: float) -> Dict[str, Any]:
        """Return a serializable dictionary snapshot of the grid state."""
        rocof = self.compute_rocof(window_points=5)
        return {
            "time": round(self.t, 2),
            "frequency": round(self.f, 3),
            "rocof": round(rocof, 3),
            "generation_pu": round(self.get_generation_supply(self.t) + self.pg, 3),
            "load_pu": round(total_load_pu, 3),
            "collapsed": self.collapsed,
            "metrics": {
                "nadir": round(self.nadir, 2),
                "max_rocof": round(self.max_rocof, 2),
                "recovery_time": round(self.recovery_time, 1) if self.recovery_time is not None else -1.0,
                "critical_energy_not_served_wh": round(self.critical_energy_not_served_wh, 1),
                "medical_minutes_lost": round(self.medical_minutes_lost, 1),
                "peak_post_shed_load": round(self.post_shed_peak_load, 2)
            }
        }
