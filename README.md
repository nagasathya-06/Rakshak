# ⚡ Project Rakshak (Grid-Edge)
### Edge-Intelligent Grid Resilience for Blackout-Free Smart Cities
**Aligned with UN Sustainable Development Goal 11 (Sustainable Cities & Communities) and SDG 7 (Affordable & Clean Energy)**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Three.js](https://img.shields.io/badge/Three.js-r128-black.svg)](https://threejs.org/)
[![ESP32 FreeRTOS](https://img.shields.io/badge/ESP32-FreeRTOS-red.svg)](https://www.espressif.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 1. Executive Summary

In modern solar-rich cities like Bengaluru, rooftop solar generation and renewable penetration are expanding rapidly. However, solar output fluctuates abruptly during cloud cover or sudden feeder trips. When electricity demand exceeds generation, the power grid's frequency drops below the nominal **$50.0\text{ Hz}$**.

### The Traditional Problem (Feeder-Level UFLS)
Today, utilities protect the grid from cascading blackout using **Substation Under-Frequency Load Shedding (UFLS)**. This is a crude, blunt cut:
* The substation circuit breaker trips and disconnects **entire distribution feeders and neighborhoods indiscriminately**.
* Schools, homes, medical clinics, and oxygen concentrators go dark alongside air conditioners and water heaters.
* **In one line:** *When the grid is in trouble, current systems switch off people, not appliances.*
* When power is restored, all loads restart at the exact same moment (**cold-load pickup / rebound peak**), drawing $5\times\text{--}6\times$ inrush current and tripping the grid a second time.

### The Rakshak Solution
**Project Rakshak** replaces blunt feeder-level cuts with **autonomous edge demand response**:
1. An edge controller (**ESP32**) at the building's main distribution board monitors grid frequency ($f$) and Rate of Change of Frequency ($\text{RoCoF} = \frac{df}{dt}$).
2. A single meter-level sensor uses **Non-Intrusive Load Monitoring (NILM)** to identify appliance switching events.
3. When frequency dips below **$49.60\text{ Hz}$**, the controller selectively sheds **Tier 2 deferrable loads** (ACs, water heaters, EV chargers) within $50\text{ ms}$, while guaranteeing **Tier 0 critical life-safety loads** (patient monitors, medical oxygen, medicine refrigeration, LED lights) remain powered.
4. When frequency stabilizes ($f \ge 49.90\text{ Hz}$), loads are restored via a **decentralized MAC-address hash delay algorithm**, flattening secondary demand surges without requiring central SCADA communication.

---

## 2. Research Foundation & Literature Reference

Rakshak incorporates foundational principles from the recent IEEE / Los Alamos National Laboratory publication:
> **"A Hardware-in-the-Loop Experimental Testbed using Air Conditioners for Grid Balancing"**  
> *Oluwagbemileke E. Oyefeso, Drew A. Geller, Ioannis M. Granitsas, Duncan S. Callaway, and Johanna L. Mathieu* (IEEE / arXiv:2411.11893v1, Nov 2024).

### Key Insights Borrowed from the Paper:
1. **Hardware-in-the-Loop (HIL) Co-Simulation Architecture:** Oyefeso et al. validated AC fleet demand response using 20 physical model houses linked to a virtual simulation of 523 homes. Rakshak employs the exact same architecture: our Python backend simulates a 500-home feeder into which a physical ESP32 connects (Phase 3).
2. **Compressor Lockout Protection:** The paper demonstrated that air conditioners have a physical cooldown time (~3 minutes) between being shut off and restarting to prevent motor stalling and burnout. Rakshak enforces a strict compressor lockout state in firmware and simulation.
3. **Transient Inrush Dynamics:** Compressors draw $5\times\text{--}6\times$ normal running current for 5–10 cycles upon restart. This physical reality validates Rakshak's MAC-hash staggered restoration.
4. **Decentralized Edge Autonomy:** The paper demonstrated that centralized aggregators suffer up to $10\times$ higher tracking errors when communication packet loss (5–10%) and delays occur. Rakshak operates **locally at the edge with zero network dependencies**.

---

## 3. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                      VIRTUAL GRID CO-SIMULATOR                         │
│  - Differential Swing Equation: 2H * d(df)/dt = Pm + Pg - Pe - D*df    │
│  - 500-Home Macro Feeder Aggregator (Oyefeso et al., IEEE 2024)        │
│  - Solar cloud-passing and sudden generator loss disturbance models    │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ (WebSocket / Serial @ 20 Hz)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        BUILDING EDGE CONTROLLER                        │
│                                                                        │
│  ┌───────────────────────┐             ┌────────────────────────────┐  │
│  │ Zero-Crossing / HIL   │             │   Single-Sensor NILM       │  │
│  │ Frequency Sensing     │             │   Current & Power Step     │  │
│  │ Detects f <= 49.60 Hz │             │   Inrush Transient Detect  │  │
│  └───────────┬───────────┘             └─────────────┬──────────────┘  │
│              │                                       │                 │
│              ▼                                       ▼                 │
│    [ RoCoF Predictive Trip ] ────────► [ Priority Decision Logic ]     │
│    df/dt <= -0.50 Hz/s                  - Tier 0: Critical (NEVER CUT) │
│                                         - Tier 1: Essential (Fan)      │
│                                         - Tier 2: Deferrable (AC/EV)   │
│                                                       │                │
│    [ Anti-Rebound Restore ] ◄─────────────────────────┘                │
│    Delay = Hash(MAC) % T_max                                           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ (JSON Telemetry Stream)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   3D STREET DIGITAL TWIN & DASHBOARD                   │
│  - Interactive 3D Three.js neighborhood scene with 12 buildings        │
│  - Bedside vital monitor displaying live patient ECG flatline dynamics │
│  - Real-time Chart.js telemetry (Frequency, RoCoF, Feeder Active Power)│
│  - Comparative evaluation table & metrics logger                       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 3-Tier Priority Matrix

| Tier | Priority | Typical Appliances | Behavior in Under-Frequency Event ($f \le 49.60\text{ Hz}$) |
| :---: | :--- | :--- | :--- |
| **Tier 0** | **Critical (Life-Safety)** | Oxygen concentrators, patient vitals monitor, medicine refrigeration, emergency lights | **Guaranteed ALWAYS ON**. Never shed under any circumstance. |
| **Tier 1** | **Essential** | Ceiling fans, basic room sockets, ventilation | Kept ON during normal dips; shed only if grid reaches extreme collapse ($f < 49.20\text{ Hz}$). |
| **Tier 2** | **Deferrable** | Air conditioners, water heaters/geysers, EV chargers | **Shed immediately within 50ms**. Subject to compressor lockout cooldown. |

---

## 5. Comparative Performance Benchmarks

Results obtained from running an identical **18% sudden generation loss** at $t = 5.0\text{ s}$ through the simulation engine:

| Evaluation Metric | 1. No Protection | 2. Conventional Feeder UFLS | 3. Rakshak DR (MAC-Hash Staggered) | 4. Rakshak DR (No Staggering) |
| :--- | :---: | :---: | :---: | :---: |
| **Frequency Nadir (Lowest Hz)** | $48.52\text{ Hz}$ | $49.19\text{ Hz}$ | **$49.70\text{ Hz}$ (Best)** | $49.63\text{ Hz}$ |
| **Max RoCoF ($\frac{df}{dt}$)** | $0.87\text{ Hz/s}$ | $0.89\text{ Hz/s}$ | $4.03\text{ Hz/s}$ | $4.80\text{ Hz/s}$ |
| **Recovery to $49.9\text{ Hz}$** | $63.0\text{ s}$ | $4.0\text{ s}$ | **$31.3\text{ s}$ (Stable)** | $15.6\text{ s}$ |
| **Medical Life-Safety Interrupted** | **100% Interrupted** | **50% Interrupted (2.1 min)** | **0% Interrupted (0.0 min)** | **0% Interrupted** |
| **Secondary Rebound Surge** | N/A (Collapse) | $100\%$ | **$115\%$ (Smooth, Safe)** | **$165\%$ (Severe Surge)** |

> **Key Takeaway:** Mode 3 (Rakshak) keeps **zero medical devices disconnected**, raises the frequency nadir, and prevents the $165\%$ secondary surge that causes re-tripping in unstaggered systems.

---

## 6. Repository Structure

```
Rakshak/
├── backend/
│   ├── config.py                 # Grid constants (H=5s, D=1), thresholds, appliance catalog
│   ├── grid_engine.py            # High-fidelity Swing Equation numerical integrator
│   ├── fleet_simulator.py        # 500-home macro fleet + 12-building micro street model
│   ├── nilm_engine.py            # Non-Intrusive Load Monitoring step & inrush detector
│   ├── hil_bridge.py             # Hardware-in-the-Loop bridge (ESP32 Serial / TCP port)
│   ├── main.py                   # FastAPI server with WebSocket streaming @ 20 Hz
│   └── requirements.txt          # Python dependencies
├── frontend/
│   ├── index.html                # Enhanced 3D Street Digital Twin (Three.js + Dual Mode)
│   └── dashboard.html            # 2D Analytical comparative dashboard (Chart.js)
├── firmware/
│   ├── esp32_rakshak_edge/
│   │   ├── esp32_rakshak_edge.ino # Dual-Core FreeRTOS C++ firmware for ESP32
│   │   ├── config.h               # GPIO pin mappings and frequency trip settings
│   │   └── nilm_edge.h            # Edge power step detection logic
│   └── README.md                  # Hardware wiring schematic & safety guidelines
├── benchmarks/
│   └── benchmark_modes.py         # Automated headless 4-mode benchmark runner
├── docs/
│   ├── architecture.md            # Detailed CS & Distributed Systems architecture
│   ├── research_insights.md       # In-depth analysis of Oyefeso et al. (IEEE 2024)
│   └── presentation_guide.md      # Evaluator pitch script, demo plan, and viva Q&A
├── run_sim.py                     # One-click launcher (backend + browser twin)
├── .gitignore                     # Git configuration
└── README.md                      # Project documentation
```

---

## 7. Quick Start Guide

### Option A: Standalone 3D Digital Twin (Zero Dependencies)
You can run the digital twin directly without installing any software:
1. Navigate to the `frontend/` folder.
2. Double-click `index.html` to open it in any modern browser (Chrome, Firefox, Edge, Safari).
3. The built-in JavaScript physics engine will simulate the street, grid swing dynamics, and load shedding automatically!

### Option B: Full Python Co-Simulation (Recommended for Phase-2 Demo)
To run the complete client-server architecture with the 500-home fleet simulation:
```bash
# 1. Clone repository
git clone https://github.com/nagasathya-06/Rakshak.git
cd Rakshak

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Launch one-click application runner
python run_sim.py
```
This starts the FastAPI backend on `http://localhost:8000` and automatically opens the 3D Digital Twin in your browser with live WebSocket telemetry.

### Option C: Run Headless Benchmark Suite
To generate quantitative numbers for project reports and presentations:
```bash
python benchmarks/benchmark_modes.py
```

---

## 8. Phase 3 Hardware Roadmap

For Phase 3 (Hardware Implementation):
1. **Controller:** ESP32 DevKit V1 (Dual Core 240MHz).
2. **Current & Voltage Sensor:** INA219 (I2C) or ZMPT101B + SCT-013 CT clamp.
3. **Actuator:** 4-Channel 5V optocoupled relay module.
4. **Proxy Benchtop Loads (Safe 12V DC):**
   * *Critical (Tier 0):* High-efficiency LED + Simulated Oximeter OLED display.
   * *Essential (Tier 1):* 12V DC cooling fan.
   * *Deferrable (Tier 2):* 12V PTC ceramic heating pad (proxy for water heater / AC).
5. **HIL Bridge:** The `hil_bridge.py` module in this repository will stream simulated grid frequency to the ESP32 over USB serial, allowing the physical board to act as Building #1 in the 500-home simulated fleet!

---

## 9. Alignment with United Nations SDGs

* **SDG 11: Sustainable Cities & Communities (Target 11.B):** Increases urban infrastructure resilience to climate extremes and power disturbances while preventing blackouts in critical healthcare facilities.
* **SDG 7: Affordable & Clean Energy (Target 7.2):** Enables Indian distribution networks (e.g., BESCOM in Bengaluru) to integrate higher levels of variable rooftop solar without sacrificing grid stability.

---

## 10. Contributors & Acknowledgments
* **Project Lead:** Nagasathya ([@nagasathya-06](https://github.com/nagasathya-06))
* **Institution:** RV College of Engineering, Bengaluru
* **Course:** Experiential Learning (EL Phase-I / Phase-II), 5th Semester Computer Science
* **Reference Paper:** Oyefeso et al., *"A Hardware-in-the-Loop Experimental Testbed using Air Conditioners for Grid Balancing"*, IEEE / Los Alamos National Laboratory, 2024.
