"""
Project Rakshak - FastAPI Simulation Backend & WebSocket Telemetry Server
Coordinates the Grid Dynamics Engine, Multi-Building Fleet, NILM Engine, and HIL Bridge.
"""

import asyncio
import json
import os
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import GridConfig
from grid_engine import GridEngine
from fleet_simulator import FleetSimulator
from nilm_engine import NILMDisaggregator
from hil_bridge import HILBridge

app = FastAPI(title="Project Rakshak - Grid Resilience Digital Twin Backend")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simulation Controller State
class SimulationController:
    def __init__(self):
        self.config = GridConfig()
        self.grid = GridEngine(self.config)
        self.fleet = FleetSimulator(self.config)
        self.nilm = NILMDisaggregator()
        self.hil = HILBridge()
        self.mode = "rakshak"  # 'none', 'ufls', 'rakshak', 'rakshak_unstaggered'
        self.running = True
        self.playback_speed = 1.0
        self.generation_loss = 0.18
        self.t_recover = 45.0

    def reset(self):
        self.grid.reset(loss=self.generation_loss, t_trip=5.0, t_rec=self.t_recover)
        self.fleet.init_fleet()
        self.nilm = NILMDisaggregator()

sim = SimulationController()


class ScenarioRequest(BaseModel):
    mode: str
    generation_loss: float = 0.18
    t_recover: float = 45.0
    shed_threshold: float = 49.60
    grid_inertia_h: float = 5.0


@app.get("/api/status")
async def get_status():
    """Return high-level simulation state."""
    state = sim.grid.get_state(1.0)
    state["mode"] = sim.mode
    state["hil_status"] = sim.hil.last_hardware_telemetry
    return state


@app.post("/api/scenario")
async def set_scenario(req: ScenarioRequest):
    """Change simulation scenario parameters."""
    if req.mode in ["none", "ufls", "rakshak", "rakshak_unstaggered"]:
        sim.mode = req.mode
    sim.generation_loss = req.generation_loss
    sim.t_recover = req.t_recover
    sim.config.threshold_smart_shed = req.shed_threshold
    sim.config.H = req.grid_inertia_h
    sim.reset()
    return {"status": "ok", "mode": sim.mode}


@app.post("/api/reset")
async def reset_simulation():
    """Reset the digital twin simulation."""
    sim.reset()
    return {"status": "reset_complete"}


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """
    Real-time high-speed telemetry feed for the 3D Digital Twin and Analytics Dashboard.
    Streams at 20 Hz (dt = 50ms).
    """
    await websocket.accept()
    try:
        while True:
            # Check for client messages (play/pause/controls) without blocking
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.001)
                data = json.loads(msg)
                action = data.get("action")
                if action == "SET_MODE":
                    sim.mode = data.get("mode", sim.mode)
                    sim.reset()
                elif action == "RESET":
                    sim.reset()
                elif action == "SET_PARAMS":
                    if "loss" in data:
                        sim.generation_loss = float(data["loss"])
                    if "trec" in data:
                        sim.t_recover = float(data["trec"])
                    if "thr" in data:
                        sim.config.threshold_smart_shed = float(data["thr"])
                    if "H" in data:
                        sim.config.H = float(data["H"])
                    sim.reset()
            except asyncio.TimeoutError:
                pass

            if sim.running:
                current_t = sim.grid.t
                dt = sim.grid.dt
                grid_f = sim.grid.f
                rocof = sim.grid.compute_rocof()

                # Step the 500-home fleet & micro-buildings
                load_pu = sim.fleet.step(current_t, dt, grid_f, rocof, sim.mode)

                # Send virtual frequency to physical ESP32 (HIL)
                sim.hil.send_grid_state(current_t, grid_f, rocof)
                hw_data = sim.hil.poll_hardware_response()

                # Step the Grid Swing Equation
                grid_state = sim.grid.step(load_pu)

                # Feed House 1 total power into Edge NILM disaggregator
                b1 = sim.fleet.micro_buildings[1]
                b1_power = b1.get_total_power_w(current_t)
                nilm_event = sim.nilm.feed_sample(current_t, b1_power, b1_power / 230.0)

                # Construct micro building statuses for Three.js 3D representation
                micro_states = []
                for b in sim.fleet.micro_buildings:
                    b_active_devs = {k: dev.is_on for k, dev in b.devices.items()}
                    b_power = b.get_total_power_w(current_t)
                    micro_states.append({
                        "i": b.idx,
                        "type": b.b_type,
                        "energized": b.energized and not sim.grid.collapsed,
                        "power_w": round(b_power, 1),
                        "devices": b_active_devs,
                        "feeder": b.feeder_idx,
                        "mac": b.mac,
                        "is_med": b.is_medical
                    })

                telemetry = {
                    "time": round(current_t, 2),
                    "frequency": round(grid_f, 3),
                    "rocof": round(rocof, 3),
                    "generation_pu": grid_state["generation_pu"],
                    "load_pu": grid_state["load_pu"],
                    "collapsed": grid_state["collapsed"],
                    "mode": sim.mode,
                    "metrics": grid_state["metrics"],
                    "buildings": micro_states,
                    "nilm_breakdown": sim.nilm.get_tier_breakdown_w(),
                    "nilm_event": nilm_event,
                    "hil": hw_data
                }

                await websocket.send_text(json.dumps(telemetry))

            await asyncio.sleep(0.05 / sim.playback_speed)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# Serve Frontend Static Directory
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
