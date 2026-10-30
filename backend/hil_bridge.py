"""
Project Rakshak - Hardware-in-the-Loop (HIL) Serial/TCP Bridge
Allows physical ESP32 edge microcontroller (Phase 3) to interface directly
with the Python Co-Simulation and Digital Twin environment.
"""

import json
import time
from typing import Optional, Dict, Any

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


class HILBridge:
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.is_connected = False
        self.last_hardware_telemetry: Dict[str, Any] = {
            "connected": False,
            "node_id": "esp32_rakshak_01",
            "relay_l3_deferrable": False,  # True = Shed/Cut, False = Normal/Powered
            "relay_l2_essential": False,
            "relay_l1_critical": False,
            "measured_current_a": 0.0,
            "measured_power_w": 0.0,
            "state": "SIMULATED"
        }

        if HAS_SERIAL and port:
            self.connect(port)

    def connect(self, port: str) -> bool:
        """Attempt connection to physical ESP32 on specified COM port."""
        if not HAS_SERIAL:
            return False
        try:
            self.ser = serial.Serial(port, self.baudrate, timeout=0.05)
            self.is_connected = True
            self.port = port
            self.last_hardware_telemetry["connected"] = True
            self.last_hardware_telemetry["state"] = "HARDWARE_ACTIVE"
            return True
        except Exception:
            self.is_connected = False
            return False

    def send_grid_state(self, timestamp: float, frequency: float, rocof: float):
        """Send virtual grid telemetry packet to the physical ESP32."""
        if not self.is_connected or not self.ser:
            return

        packet = {
            "t": round(timestamp, 2),
            "f": round(frequency, 3),
            "df": round(rocof, 3)
        }
        msg = (json.dumps(packet) + "\n").encode("utf-8")
        try:
            self.ser.write(msg)
        except Exception:
            self.is_connected = False
            self.last_hardware_telemetry["connected"] = False

    def poll_hardware_response(self) -> Dict[str, Any]:
        """Read relay switching and load measurements from the physical ESP32."""
        if not self.is_connected or not self.ser:
            return self.last_hardware_telemetry

        try:
            while self.ser.in_waiting > 0:
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if line.startswith("{") and line.endswith("}"):
                    data = json.loads(line)
                    self.last_hardware_telemetry.update(data)
                    self.last_hardware_telemetry["connected"] = True
                    self.last_hardware_telemetry["state"] = "HARDWARE_ACTIVE"
        except Exception:
            pass

        return self.last_hardware_telemetry
