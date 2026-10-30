"""
Project Rakshak - Single-Sensor NILM (Non-Intrusive Load Monitoring) Disaggregation Engine
Identifies appliance state changes and categorizes active loads into
Tier 0 (Critical), Tier 1 (Essential), and Tier 2 (Deferrable) from aggregate power telemetry.
"""

from typing import Dict, List, Any, Optional
import numpy as np
from config import APPLIANCE_CATALOG


class NILMDisaggregator:
    def __init__(self, sample_rate_hz: float = 20.0):
        self.sample_rate = sample_rate_hz
        self.buffer_size = int(sample_rate_hz * 1.5)  # 1.5-second sliding window
        self.power_buffer: List[float] = []
        self.current_buffer: List[float] = []
        self.active_appliances: Dict[str, bool] = {k: False for k in APPLIANCE_CATALOG.keys()}
        self.event_log: List[Dict[str, Any]] = []

    def feed_sample(self, timestamp: float, aggregate_power_w: float, aggregate_current_a: float) -> Optional[Dict[str, Any]]:
        """
        Process a single sensor sample (Power, Current) from the meter.
        Returns a detected event dict if a switching event occurred.
        """
        self.power_buffer.append(aggregate_power_w)
        self.current_buffer.append(aggregate_current_a)

        if len(self.power_buffer) > self.buffer_size:
            self.power_buffer.pop(0)
            self.current_buffer.pop(0)

        if len(self.power_buffer) < 5:
            return None

        # Calculate differential power step over last 200ms
        delta_p = self.power_buffer[-1] - self.power_buffer[-4]
        peak_current = max(self.current_buffer[-4:])
        steady_current = self.current_buffer[-1]
        inrush_ratio = (peak_current / max(steady_current, 0.01)) if steady_current > 0.1 else 1.0

        detected_event = None

        # ON-event detection threshold (> 40 W step change)
        if delta_p > 40.0:
            best_match = None
            best_diff = float("inf")

            for app_key, spec in APPLIANCE_CATALOG.items():
                if not self.active_appliances[app_key]:
                    # Difference between observed step and known appliance rating
                    p_diff = abs(delta_p - spec["power_w"])
                    if p_diff < best_diff and p_diff < spec["power_w"] * 0.4:
                        best_diff = p_diff
                        best_match = app_key

            if best_match:
                self.active_appliances[best_match] = True
                detected_event = {
                    "timestamp": round(timestamp, 2),
                    "type": "LOAD_ON",
                    "appliance": best_match,
                    "name": APPLIANCE_CATALOG[best_match]["name"],
                    "tier": APPLIANCE_CATALOG[best_match]["tier"],
                    "delta_p": round(delta_p, 1),
                    "inrush_ratio": round(inrush_ratio, 2)
                }
                self.event_log.append(detected_event)

        # OFF-event detection threshold (< -40 W step change)
        elif delta_p < -40.0:
            step_abs = abs(delta_p)
            best_match = None
            best_diff = float("inf")

            for app_key, spec in APPLIANCE_CATALOG.items():
                if self.active_appliances[app_key]:
                    p_diff = abs(step_abs - spec["power_w"])
                    if p_diff < best_diff and p_diff < spec["power_w"] * 0.4:
                        best_diff = p_diff
                        best_match = app_key

            if best_match:
                self.active_appliances[best_match] = False
                detected_event = {
                    "timestamp": round(timestamp, 2),
                    "type": "LOAD_OFF",
                    "appliance": best_match,
                    "name": APPLIANCE_CATALOG[best_match]["name"],
                    "tier": APPLIANCE_CATALOG[best_match]["tier"],
                    "delta_p": round(delta_p, 1),
                    "inrush_ratio": 1.0
                }
                self.event_log.append(detected_event)

        return detected_event

    def get_tier_breakdown_w(self) -> Dict[str, float]:
        """Compute estimated power breakdown by priority tier."""
        breakdown = {"tier_0_critical": 0.0, "tier_1_essential": 0.0, "tier_2_deferrable": 0.0}
        for key, is_on in self.active_appliances.items():
            if is_on:
                tier = APPLIANCE_CATALOG[key]["tier"]
                w = APPLIANCE_CATALOG[key]["power_w"]
                if tier == 0:
                    breakdown["tier_0_critical"] += w
                elif tier == 1:
                    breakdown["tier_1_essential"] += w
                elif tier == 2:
                    breakdown["tier_2_deferrable"] += w
        return breakdown
